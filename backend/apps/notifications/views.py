from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import services
from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["notification_type", "is_read"]

    def get_queryset(self):
        user = self.request.user
        return Notification.objects.filter(company_id=user.company_id).filter(
            Q(recipient=user) | Q(recipient__isnull=True)
        )

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        return Response({"count": self.get_queryset().filter(is_read=False).count()})

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(is_read=False).update(is_read=True, read_at=timezone.now())
        return Response({"updated": updated})

    @action(detail=False, methods=["post"])
    def scan_overdue(self, request):
        """Simulates the periodic sweep a Celery beat schedule would run --
        raises overdue-invoice reminders for this company right now."""
        created = services.scan_overdue_invoices(company=request.user.company)
        return Response({"created": len(created)})
