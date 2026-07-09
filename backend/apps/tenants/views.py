from rest_framework import permissions
from rest_framework.generics import RetrieveUpdateAPIView

from apps.core.viewsets import CompanyScopedViewSet

from .models import Branch, Company
from .serializers import BranchSerializer, CompanySerializer


class CompanyMeView(RetrieveUpdateAPIView):
    """The authenticated user's own company profile (settings screen)."""

    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.company


class BranchViewSet(CompanyScopedViewSet):
    queryset = Branch.objects.select_related("company").all()
    serializer_class = BranchSerializer
    filterset_fields = ["is_active", "is_main"]
    search_fields = ["name", "code", "city"]
