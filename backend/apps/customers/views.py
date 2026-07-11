from apps.core.viewsets import CompanyScopedViewSet
from apps.portal.staff import PortalAccessMixin

from .models import Customer, CustomerGroup
from .serializers import CustomerGroupSerializer, CustomerSerializer


class CustomerGroupViewSet(CompanyScopedViewSet):
    queryset = CustomerGroup.objects.all()
    serializer_class = CustomerGroupSerializer
    permission_module = "customers"
    search_fields = ["name"]


class CustomerViewSet(PortalAccessMixin, CompanyScopedViewSet):
    queryset = Customer.objects.select_related("group").all()
    serializer_class = CustomerSerializer
    permission_module = "customers"
    filterset_fields = ["group", "is_active"]
    search_fields = ["name", "phone", "email", "tin_number"]
    portal_owner_field = "customer"
