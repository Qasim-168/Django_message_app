"""
JWT authentication middleware for Django Channels WebSocket connections.

Reads the JWT access token from the query string parameter ``token``
and attaches the authenticated user to ``scope["user"]``.
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_str):
    """Validate a raw JWT string and return the corresponding User."""
    try:
        validated = AccessToken(token_str)
        return User.objects.get(pk=validated["user_id"])
    except (TokenError, InvalidToken, User.DoesNotExist, KeyError):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Extract ``?token=<jwt>`` from the WebSocket query string, validate it,
    and place the authenticated user into ``scope["user"]``.
    """

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        token_list = params.get("token", [])

        if token_list:
            scope["user"] = await get_user_from_token(token_list[0])
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)
