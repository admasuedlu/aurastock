from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.tenants.models import SubscriptionPlan

# (code, name, monthly price ETB, max_users, max_branches, max_warehouses)
# "trial" matches the plan the signup flow auto-assigns (get_or_create by code).
PLANS = [
    ("trial", "Free Trial", Decimal("0"), 5, 1, 1),
    ("starter", "Starter", Decimal("799"), 5, 2, 3),
    ("business", "Business", Decimal("2499"), 20, 5, 10),
    ("enterprise", "Enterprise", Decimal("7999"), 200, 50, 100),
]


class Command(BaseCommand):
    help = "Seed the default subscription plan tiers (idempotent; existing plans are left untouched)."

    def handle(self, *args, **options):
        created = 0
        for code, name, price, max_users, max_branches, max_warehouses in PLANS:
            _, was_created = SubscriptionPlan.objects.get_or_create(
                code=code,
                defaults={
                    "name": name, "price_monthly_etb": price, "max_users": max_users,
                    "max_branches": max_branches, "max_warehouses": max_warehouses,
                },
            )
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(
            f"Seeded plans: {created} created, {len(PLANS) - created} already existed."
        ))
