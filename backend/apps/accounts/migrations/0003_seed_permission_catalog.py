from django.db import migrations

from apps.accounts.permissions_catalog import ACTIONS, MODULES, permission_code


def seed_permissions(apps, schema_editor):
    """Populate the global permission catalog so role grants (and therefore
    per-endpoint enforcement) work in every environment, tests included --
    previously this only happened when someone ran `manage.py seed_permissions`."""
    Permission = apps.get_model("accounts", "Permission")
    for module in MODULES:
        for action in ACTIONS:
            Permission.objects.get_or_create(
                code=permission_code(module, action),
                defaults={"module": module, "description": f"Can {action} {module}"},
            )


def unseed(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    codes = [permission_code(m, a) for m in MODULES for a in ACTIONS]
    Permission.objects.filter(code__in=codes).delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_alter_user_email")]
    operations = [migrations.RunPython(seed_permissions, unseed)]
