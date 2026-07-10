from rest_framework.permissions import BasePermission

from .models import PortalAccount


class IsPortalCustomer(BasePermission):
    """A logged-in portal account acting for a customer. A staff JWT
    authenticates as a plain User (not a PortalAccount), so it fails this
    check by construction -- same for a supplier's portal token."""

    def has_permission(self, request, view):
        account = request.user
        return isinstance(account, PortalAccount) and account.customer_id is not None


class IsPortalSupplier(BasePermission):
    def has_permission(self, request, view):
        account = request.user
        return isinstance(account, PortalAccount) and account.supplier_id is not None
