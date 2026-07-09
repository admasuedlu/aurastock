from django.core.management.base import BaseCommand

from apps.accounts.models import Permission
from apps.accounts.permissions_catalog import ACTIONS, MODULES, permission_code


class Command(BaseCommand):
    help = "Seed the global permission catalog (module.action pairs)."

    def handle(self, *args, **options):
        created = 0
        for module in MODULES:
            for action in ACTIONS:
                _, was_created = Permission.objects.get_or_create(
                    code=permission_code(module, action),
                    defaults={"module": module, "description": f"Can {action} {module}"},
                )
                created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Seeded permissions: {created} created, "
                                              f"{len(MODULES) * len(ACTIONS) - created} already existed."))
