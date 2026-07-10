from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.authentication import company_is_blocked


class TenantAwareTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Blocks login (not just API use) for users of a suspended tenant, so
    they get a clear message at the door instead of a valid token that then
    403s on every request."""

    def validate(self, attrs):
        data = super().validate(attrs)
        if company_is_blocked(self.user.company):
            raise AuthenticationFailed(
                "This company's subscription is suspended. Contact support.",
                code="company_suspended",
            )
        return data


class TenantAwareTokenObtainPairView(TokenObtainPairView):
    serializer_class = TenantAwareTokenObtainPairSerializer
