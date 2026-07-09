from apps.core.viewsets import CompanyScopedViewSet

from .models import Supplier
from .serializers import SupplierSerializer


class SupplierViewSet(CompanyScopedViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    filterset_fields = ["is_active"]
    search_fields = ["name", "phone", "email", "tin_number"]
