"""API authentication helpers."""

from rest_framework.authentication import TokenAuthentication


class BearerTokenAuthentication(TokenAuthentication):
    """Accept Authorization: Bearer <token> in addition to Token <token>."""

    keyword = "Bearer"
