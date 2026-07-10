from rest_framework.permissions import BasePermission


class IsPlatformAdmin(BasePermission):
    """Platform-level staff only: users with no company FK (they belong to
    the SaaS operator, not any tenant) and the staff flag. A tenant user can
    never satisfy this, no matter what role their company gave them."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.is_staff and user.company_id is None
        )
