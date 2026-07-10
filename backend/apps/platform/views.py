from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, ProtectedError, Q
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.models import Company, SubscriptionPlan

from .permissions import IsPlatformAdmin
from .serializers import SubscriptionPlanSerializer, TenantCompanySerializer


class PlatformOverviewView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        User = get_user_model()
        status_counts = dict(
            Company.objects.values_list("subscription_status").annotate(n=Count("id"))
        )
        thirty_days_ago = timezone.now() - timedelta(days=30)
        return Response({
            "total_companies": Company.objects.count(),
            "status_counts": status_counts,
            "total_tenant_users": User.objects.filter(company__isnull=False).count(),
            "signups_last_30_days": Company.objects.filter(created_at__gte=thirty_days_ago).count(),
        })


class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsPlatformAdmin]
    filterset_fields = ["is_active"]
    search_fields = ["name", "code"]

    def get_queryset(self):
        return SubscriptionPlan.objects.annotate(company_count=Count("companies"))

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            raise DRFValidationError(
                "This plan still has companies on it; move them to another plan first."
            )


class TenantCompanyViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                           mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Read/manage tenants. Deliberately no create (tenants self-serve via
    signup) and no delete (dropping a tenant cascades through every scoped
    table -- too destructive for a list-screen button; suspension is the tool)."""

    serializer_class = TenantCompanySerializer
    permission_classes = [IsPlatformAdmin]
    filterset_fields = ["subscription_status", "subscription_plan", "is_active"]
    search_fields = ["name", "slug", "email", "phone", "tin_number"]

    def get_queryset(self):
        return Company.objects.select_related("subscription_plan").annotate(
            user_count=Count("users", distinct=True),
            branch_count=Count("tenants_branch_set", distinct=True),
            warehouse_count=Count("inventory_warehouse_set", distinct=True),
        ).order_by("-created_at")

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        company = self.get_object()
        company.subscription_status = Company.SubscriptionStatus.SUSPENDED
        company.save(update_fields=["subscription_status", "updated_at"])
        return Response(self.get_serializer(self.get_queryset().get(pk=company.pk)).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        company = self.get_object()
        company.subscription_status = Company.SubscriptionStatus.ACTIVE
        company.save(update_fields=["subscription_status", "updated_at"])
        return Response(self.get_serializer(self.get_queryset().get(pk=company.pk)).data)

    @action(detail=True, methods=["post"], url_path="change-plan")
    def change_plan(self, request, pk=None):
        company = self.get_object()
        plan_id = request.data.get("plan")
        if not plan_id:
            raise DRFValidationError({"plan": "This field is required."})
        try:
            plan = SubscriptionPlan.objects.get(pk=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            raise DRFValidationError({"plan": "No active plan with that id."})
        company.subscription_plan = plan
        company.save(update_fields=["subscription_plan", "updated_at"])
        return Response(self.get_serializer(self.get_queryset().get(pk=company.pk)).data)
