from rest_framework.decorators import action
from rest_framework.response import Response

from . import services
from .models import PortalAccount
from .serializers import PortalAccessGrantSerializer, PortalAccountStaffSerializer


class PortalAccessMixin:
    """Adds a `portal-access` action to a CompanyScopedViewSet for customers
    or suppliers. Because get_object() already scopes to the staff member's
    own company, a customer/supplier from another tenant 404s -- so staff
    can't attach a portal login to someone else's record.

    Set `portal_owner_field` to "customer" or "supplier" on the viewset."""

    portal_owner_field = None

    @action(detail=True, methods=["get", "post", "delete"], url_path="portal-access")
    def portal_access(self, request, pk=None):
        owner = self.get_object()
        field = self.portal_owner_field

        if request.method == "GET":
            account = PortalAccount.objects.filter(**{field: owner}).first()
            if account is None:
                return Response({"has_access": False})
            return Response({"has_access": True, **PortalAccountStaffSerializer(account).data})

        if request.method == "DELETE":
            services.revoke_portal_access(**{field: owner})
            return Response({"has_access": False})

        serializer = PortalAccessGrantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = services.grant_portal_access(
            **{field: owner},
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        return Response({"has_access": True, **PortalAccountStaffSerializer(account).data})
