from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


def company_is_blocked(company) -> bool:
    """A tenant is locked out when the platform admin suspended it or
    deactivated it outright. Platform staff have no company, so they can
    never be blocked by this."""
    from apps.tenants.models import Company

    if company is None:
        return False
    return (
        not company.is_active
        or company.subscription_status == Company.SubscriptionStatus.SUSPENDED
    )


class TenantAwareJWTAuthentication(JWTAuthentication):
    """JWT auth that also rejects users of suspended/deactivated tenants.
    Enforced here (the default authentication class) rather than in a
    permission class, because several views set their own permission_classes
    and a default permission would silently not apply to them."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if company_is_blocked(user.company):
            raise AuthenticationFailed(
                "This company's subscription is suspended. Contact support.",
                code="company_suspended",
            )
        return user
