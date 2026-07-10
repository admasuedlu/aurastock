from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import Notification
from .serializers import NotificationSerializer


def _broadcast(notification: Notification) -> None:
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    # Personal notifications (recipient set) only go to that user's own
    # socket group; company-wide ones (e.g. low stock) go to everyone
    # connected for that tenant. Keeps a reminder addressed to one salesperson
    # from flashing across every other user's screen in the company.
    group = (
        f"user-{notification.recipient_id}-notifications" if notification.recipient_id
        else f"company-{notification.company_id}-notifications"
    )
    async_to_sync(channel_layer.group_send)(
        group, {"type": "notification.new", "data": NotificationSerializer(notification).data},
    )


def _send_email(notification: Notification) -> None:
    if notification.recipient_id:
        recipients = [notification.recipient.email] if notification.recipient.email else []
    else:
        recipients = list(
            notification.company.users.exclude(email="").values_list("email", flat=True)
        )
    if not recipients:
        return
    send_mail(
        subject=notification.title,
        message=notification.message,
        from_email=None,
        recipient_list=recipients,
        fail_silently=True,
    )


def create_notification(
    *, company, notification_type, title, message="", reference="", recipient=None,
    dedupe=True, email=False,
) -> Notification | None:
    """Dedupe means: don't create a second notification for the same
    (company, type, reference) while an earlier one is still unread -- so a
    low-stock item that keeps selling doesn't spam a new row on every sale,
    but does alert again once the existing one has been acknowledged."""
    if dedupe and reference:
        already_pending = Notification.objects.filter(
            company=company, notification_type=notification_type, reference=reference, is_read=False,
        ).exists()
        if already_pending:
            return None

    notification = Notification.objects.create(
        company=company, recipient=recipient, notification_type=notification_type,
        title=title, message=message, reference=reference,
    )
    # stock_out() (and therefore notify_low_stock) often runs inside an outer
    # @transaction.atomic block it doesn't own (invoice confirm looping over
    # line items, POS checkout) -- defer the push/email until that outer
    # transaction actually commits, so a later rollback can't leave a "ghost"
    # notification for a change that never persisted.
    transaction.on_commit(lambda: _broadcast(notification))
    if email:
        transaction.on_commit(lambda: _send_email(notification))
    return notification


def notify_low_stock(*, stock_item) -> Notification | None:
    product = stock_item.product
    return create_notification(
        company=stock_item.company,
        notification_type=Notification.NotificationType.LOW_STOCK,
        title=f"Low stock: {product.name}",
        message=(
            f"{product.name} at {stock_item.warehouse.name} is down to "
            f"{stock_item.quantity_on_hand} units (reorder level {product.reorder_level})."
        ),
        reference=f"stockitem:{stock_item.id}",
        email=True,
    )


def scan_overdue_invoices(*, company) -> list[Notification]:
    """Finds confirmed/partially-paid invoices past their due date and raises
    a reminder for each one not already pending. Intended to be called
    periodically (a Celery beat schedule would call this; none is wired up
    yet, so for now it's a POST endpoint that simulates that run)."""
    from apps.sales.models import Invoice

    today = timezone.localdate()
    overdue = Invoice.objects.filter(
        company=company, due_date__lt=today,
        status__in=[Invoice.Status.CONFIRMED, Invoice.Status.PARTIALLY_PAID],
    ).select_related("customer", "created_by")

    created = []
    for invoice in overdue:
        days_overdue = (today - invoice.due_date).days
        notification = create_notification(
            company=company,
            notification_type=Notification.NotificationType.OVERDUE_INVOICE,
            title=f"Invoice {invoice.number} overdue",
            message=(
                f"{invoice.customer.name} owes {invoice.balance_due} ETB on {invoice.number}, "
                f"due {days_overdue} day(s) ago."
            ),
            reference=invoice.number,
            recipient=invoice.created_by,
            email=True,
        )
        if notification is not None:
            created.append(notification)
    return created
