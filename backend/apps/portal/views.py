from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.purchasing.models import PurchaseOrder
from apps.sales.models import Invoice, Quotation, SalesOrder

from . import services
from .authentication import PortalTokenAuthentication
from .models import PortalAccount
from .permissions import IsPortalCustomer, IsPortalSupplier
from .serializers import (
    PortalInvoiceSerializer,
    PortalLoginSerializer,
    PortalPurchaseOrderSerializer,
    PortalQuotationSerializer,
    PortalSalesOrderSerializer,
)
from .tokens import issue_portal_token


class PortalLoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = PortalLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        # One generic failure message whether the email is unknown or the
        # password is wrong, so the portal isn't an account-enumeration oracle.
        try:
            account = PortalAccount.objects.select_related(
                "company", "customer", "supplier"
            ).get(email__iexact=email, is_active=True)
        except PortalAccount.DoesNotExist:
            raise DRFValidationError("Invalid email or password.")

        from apps.core.authentication import company_is_blocked

        if company_is_blocked(account.company) or not account.check_password(password):
            raise DRFValidationError("Invalid email or password.")

        account.last_login_at = timezone.now()
        account.save(update_fields=["last_login_at"])
        return Response({
            "token": issue_portal_token(account),
            "account_type": account.account_type,
            "display_name": account.display_name,
            "email": account.email,
        })


class _PortalViewSetBase(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    authentication_classes = [PortalTokenAuthentication]


class PortalCustomerViewSetBase(_PortalViewSetBase):
    permission_classes = [IsPortalCustomer]

    def base_queryset(self):
        account = self.request.user
        return self.model.objects.filter(company_id=account.company_id, customer_id=account.customer_id)


class PortalSupplierViewSetBase(_PortalViewSetBase):
    permission_classes = [IsPortalSupplier]

    def base_queryset(self):
        account = self.request.user
        return self.model.objects.filter(company_id=account.company_id, supplier_id=account.supplier_id)


class PortalQuotationViewSet(PortalCustomerViewSetBase):
    model = Quotation
    serializer_class = PortalQuotationSerializer

    def get_queryset(self):
        # Draft quotations aren't visible: the customer only sees a quote once
        # staff have actually sent it.
        return (
            self.base_queryset()
            .exclude(status=Quotation.Status.DRAFT)
            .prefetch_related("items__product")
        )

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        return self._respond(request, Quotation.Status.ACCEPTED, "accepted")

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._respond(request, Quotation.Status.REJECTED, "rejected")

    @transaction.atomic
    def _respond(self, request, new_status, verb):
        quotation = self.get_object()
        if quotation.status != Quotation.Status.SENT:
            raise DRFValidationError(
                f"Only a sent quotation can be {verb}; this one is {quotation.get_status_display().lower()}."
            )
        quotation.status = new_status
        quotation.save(update_fields=["status", "updated_at"])
        services.notify_staff_of_portal_action(
            document=quotation, actor_name=request.user.display_name,
            verb=verb, reference=quotation.number,
        )
        return Response(self.get_serializer(quotation).data)


class PortalSalesOrderViewSet(PortalCustomerViewSetBase):
    model = SalesOrder
    serializer_class = PortalSalesOrderSerializer

    def get_queryset(self):
        return self.base_queryset().prefetch_related("items__product")


class PortalInvoiceViewSet(PortalCustomerViewSetBase):
    model = Invoice
    serializer_class = PortalInvoiceSerializer

    def get_queryset(self):
        # Only invoices the customer owes on -- draft invoices aren't issued
        # yet, and a fully-paid one has no outstanding balance to show.
        return (
            self.base_queryset()
            .filter(status__in=[Invoice.Status.CONFIRMED, Invoice.Status.PARTIALLY_PAID])
            .prefetch_related("items__product")
        )


class PortalPurchaseOrderViewSet(PortalSupplierViewSetBase):
    model = PurchaseOrder
    serializer_class = PortalPurchaseOrderSerializer

    def get_queryset(self):
        # Suppliers see a PO once staff send it, never a draft still being built.
        return (
            self.base_queryset()
            .exclude(status=PurchaseOrder.Status.DRAFT)
            .prefetch_related("items__product")
        )

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def acknowledge(self, request, pk=None):
        order = self.get_object()
        if order.status != PurchaseOrder.Status.SENT:
            raise DRFValidationError(
                f"Only a sent purchase order can be acknowledged; this one is "
                f"{order.get_status_display().lower()}."
            )
        order.status = PurchaseOrder.Status.APPROVED
        order.save(update_fields=["status", "updated_at"])
        services.notify_staff_of_portal_action(
            document=order, actor_name=request.user.display_name,
            verb="acknowledged", reference=order.number,
        )
        return Response(self.get_serializer(order).data)
