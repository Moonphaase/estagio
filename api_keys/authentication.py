from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import APIKey


class APIKeyAuthentication(BaseAuthentication):
    keyword = 'Api-Key'

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith(self.keyword + ' '):
            return None   # deixa o próximo autenticador tentar (ex: JWT)

        raw_key = auth_header[len(self.keyword) + 1:].strip()
        api_key = APIKey.authenticate(raw_key)

        if api_key is None:
            raise AuthenticationFailed('API Key inválida ou expirada.')

        return (api_key.user, api_key)   # (user, auth_token)