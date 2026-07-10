from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def _get_user(user_id):
    from django.contrib.auth import get_user_model

    from apps.core.authentication import company_is_blocked

    User = get_user_model()
    try:
        user = User.objects.select_related("company").get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()
    if company_is_blocked(user.company):
        return AnonymousUser()
    return user


class JWTAuthMiddleware(BaseMiddleware):
    """Authenticates websocket connections via `?token=<access token>` since
    browsers can't set Authorization headers on WebSocket handshakes."""

    async def __call__(self, scope, receive, send):
        query_string = parse_qs(scope.get("query_string", b"").decode())
        token = query_string.get("token", [None])[0]
        scope["user"] = AnonymousUser()
        if token:
            try:
                access_token = AccessToken(token)
                scope["user"] = await _get_user(access_token["user_id"])
            except InvalidToken:
                pass
        return await super().__call__(scope, receive, send)
