from django.core import signing

# Separate from SIMPLE_JWT on purpose: portal accounts aren't Users, so they
# can't ride rest_framework_simplejwt's user-lookup machinery. A signed,
# timestamped value is enough for a short-lived external session.
PORTAL_TOKEN_SALT = "apps.portal.PortalAccount"
PORTAL_TOKEN_MAX_AGE = 60 * 60 * 12  # 12 hours


def issue_portal_token(account) -> str:
    return signing.TimestampSigner(salt=PORTAL_TOKEN_SALT).sign(str(account.id))


def read_portal_token(token: str) -> str:
    """Returns the account id encoded in the token. Raises
    signing.SignatureExpired or signing.BadSignature on failure."""
    return signing.TimestampSigner(salt=PORTAL_TOKEN_SALT).unsign(token, max_age=PORTAL_TOKEN_MAX_AGE)
