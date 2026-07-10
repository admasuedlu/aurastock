from apps.core.viewsets import CompanyScopedViewSet
from apps.portal.staff import PortalAccessMixin

from .models import Supplier
from .serializers import SupplierSerializer


class SupplierViewSet(PortalAccessMixin, CompanyScopedViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    filterset_fields = ["is_active"]
    search_fields = ["name", "phone", "email", "tin_number"]
    portal_owner_field = "supplier"
