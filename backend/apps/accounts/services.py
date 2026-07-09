from django.db import transaction

from .models import Permission, Role
from .permissions_catalog import ROLE_TEMPLATES, resolve_codes_for_role


@transaction.atomic
def seed_default_roles(company) -> dict[str, Role]:
    """Create the starter role set for a newly signed-up company."""
    roles = {}
    for name, template in ROLE_TEMPLATES.items():
        role, _ = Role.objects.get_or_create(company=company, name=name, defaults={"is_system": True})
        codes = resolve_codes_for_role(template)
        role.permissions.set(Permission.objects.filter(code__in=codes))
        roles[name] = role
    return roles
