from rest_framework.permissions import BasePermission


class IsSameCompany(BasePermission):
    """Object-level permission restricting access to rows belonging to the
    requesting user's company (tenant isolation)."""

    def has_object_permission(self, request, view, obj):
        user_company = getattr(request.user, "company_id", None)
        obj_company = getattr(obj, "company_id", None)
        return user_company is not None and user_company == obj_company


class HasRolePermission(BasePermission):
    """Checks the authenticated user's role grants the permission code
    configured on the view via `required_permission = "module.action"`."""

    def has_permission(self, request, view):
        required = getattr(view, "required_permission", None)
        if not required:
            return True
        if request.user.is_superuser:
            return True
        role = getattr(request.user, "role", None)
        if role is None:
            return False
        return role.permissions.filter(code=required).exists()
