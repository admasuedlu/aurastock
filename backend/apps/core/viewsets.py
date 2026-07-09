from rest_framework import viewsets


class CompanyScopedViewSet(viewsets.ModelViewSet):
    """Base viewset for tenant-scoped resources. Automatically restricts the
    queryset to the requesting user's company and stamps new rows with it,
    so individual views never need to remember to do tenant filtering."""

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        return qs.filter(company_id=user.company_id)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)
