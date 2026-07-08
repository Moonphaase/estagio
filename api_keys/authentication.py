from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from api_keys.models import APIKey


class APIKeyAuthentication(BaseAuthentication):
    keyword = "Token"

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        try:
            prefix, raw_key = auth_header.split(" ", 1)
        except ValueError:
            raise AuthenticationFailed("Formato inválido. Use: Authorization: Token <chave>")

        if prefix != self.keyword:
            return None

        api_key = APIKey.authenticate(raw_key)
        if api_key is None:
            raise AuthenticationFailed("API Key inválida, inativa ou expirada.")

        return (api_key.user, api_key)