from apps.core.viewsets import CompanyScopedViewSet

from .models import Customer, CustomerGroup
from .serializers import CustomerGroupSerializer, CustomerSerializer


class CustomerGroupViewSet(CompanyScopedViewSet):
    queryset = CustomerGroup.objects.all()
    serializer_class = CustomerGroupSerializer
    search_fields = ["name"]


class CustomerViewSet(CompanyScopedViewSet):
    queryset = Customer.objects.select_related("group").all()
    serializer_class = CustomerSerializer
    filterset_fields = ["group", "is_active"]
    search_fields = ["name", "phone", "email", "tin_number"]
