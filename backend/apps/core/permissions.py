from rest_framework.permissions import BasePermission

_METHOD_ACTIONS = {
    "GET": "view", "HEAD": "view", "OPTIONS": "view",
    "POST": "add", "PUT": "change", "PATCH": "change", "DELETE": "delete",
}


class HasModulePermission(BasePermission):
    """Enforces a view's `permission_module` against the user's role, using the
    seeded `module.action` catalog. The action defaults from the HTTP method
    (safe -> view, POST -> add, PUT/PATCH -> change, DELETE -> delete); a view
    can override per custom @action via `permission_action_map` (DRF action
    name -> catalog action), e.g. mapping `approve` to the "approve" action.

    A view with no `permission_module` is unguarded (returns True), so this is
    safe to install as a global default -- only annotated views are restricted.
    Superusers always pass; a user with no role is denied any guarded action."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        module = getattr(view, "permission_module", None)
        if module is None:
            return True
        if user.is_superuser:
            return True

        action = self._catalog_action(request, view)
        if action is None:
            return True

        role = getattr(user, "role", None)
        if role is None:
            return False
        return role.permissions.filter(code=f"{module}.{action}").exists()

    def _catalog_action(self, request, view):
        overrides = getattr(view, "permission_action_map", None) or {}
        view_action = getattr(view, "action", None)
        if view_action in overrides:
            return overrides[view_action]
        return _METHOD_ACTIONS.get(request.method)


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
