from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User


class Command(BaseCommand):
    help = ("Create a platform-level admin (SaaS operator staff, no company). "
            "Tenant signup can't produce one of these -- it always creates a company.")

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("password")
        parser.add_argument("--first-name", default="Platform")
        parser.add_argument("--last-name", default="Admin")

    def handle(self, *args, **options):
        email = options["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise CommandError(f"A user with email {email} already exists.")
        User.objects.create_user(
            username=email,
            email=email,
            password=options["password"],
            first_name=options["first_name"],
            last_name=options["last_name"],
            company=None,
            is_staff=True,
            is_superuser=True,
        )
        self.stdout.write(self.style.SUCCESS(f"Platform admin {email} created."))
