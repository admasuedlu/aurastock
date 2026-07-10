from django.db import IntegrityError
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.notifications.models import Notification
from apps.notifications.services import create_notification

from .models import PortalAccount


def grant_portal_access(*, customer=None, supplier=None, email, password) -> PortalAccount:
    """Creates a portal login for a customer/supplier, or resets the
    email/password of an existing one. Exactly one of customer/supplier must
    be given; the caller (a company-scoped viewset action) is what guarantees
    it belongs to the requesting staff member's own tenant."""
    owner = customer if customer is not None else supplier
    lookup = {"customer": customer} if customer is not None else {"supplier": supplier}
    try:
        account, _ = PortalAccount.objects.update_or_create(
            **lookup, defaults={"company": owner.company, "email": email, "is_active": True},
        )
    except IntegrityError:
        raise DRFValidationError({"email": "Already in use by another portal account."})
    account.set_password(password)
    account.save(update_fields=["password"])
    return account


def revoke_portal_access(*, customer=None, supplier=None) -> None:
    if customer is not None:
        PortalAccount.objects.filter(customer=customer).delete()
    else:
        PortalAccount.objects.filter(supplier=supplier).delete()


def notify_staff_of_portal_action(*, document, actor_name, verb, reference):
    """Raises a staff notification when a portal customer/supplier acts on a
    document (accept/reject a quotation, acknowledge a PO). Reuses the Phase 7
    pipeline: addressed to the document's creator where known -- otherwise
    company-wide -- so the salesperson who sent it hears back. Deduping is off
    since each action is a distinct event the staff should always see."""
    return create_notification(
        company=document.company,
        notification_type=Notification.NotificationType.SYSTEM,
        title=f"{reference} {verb}",
        message=f"{actor_name} {verb} {reference} via the portal.",
        reference=reference,
        recipient=document.created_by,
        dedupe=False,
        email=True,
    )
