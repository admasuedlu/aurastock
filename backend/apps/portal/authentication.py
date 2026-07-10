from django.core import signing
from django.core.exceptions import ValidationError
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from apps.core.authentication import company_is_blocked

from .models import PortalAccount
from .tokens import read_portal_token

KEYWORD = "Portal"


class PortalTokenAuthentication(BaseAuthentication):
    """Authenticates `Authorization: Portal <token>`. A missing header or a
    different scheme (e.g. a staff `Bearer` JWT) is not this authenticator's
    business -- it returns None so DRF treats the request as unauthenticated
    for portal endpoints, which only ever configure this authenticator. A
    `Portal`-scheme header with a bad/expired token is this authenticator's
    business, so it raises rather than silently passing through."""

    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        parts = header.split()
        if len(parts) != 2 or parts[0] != KEYWORD:
            return None

        token = parts[1]
        try:
            account_id = read_portal_token(token)
        except signing.SignatureExpired:
            raise AuthenticationFailed("Portal session expired, please log in again.")
        except signing.BadSignature:
            raise AuthenticationFailed("Invalid portal token.")

        try:
            account = PortalAccount.objects.select_related(
                "company", "customer", "supplier"
            ).get(pk=account_id)
        except (PortalAccount.DoesNotExist, ValidationError, ValueError):
            raise AuthenticationFailed("Invalid portal token.")

        if not account.is_active or company_is_blocked(account.company):
            raise AuthenticationFailed("This portal account is no longer active.")

        return (account, None)
