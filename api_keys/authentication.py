from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from api_keys.models import APIKey


class APIKeyAuthentication(BaseAuthentication):
    keyword = "Token"

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization", "").strip()
        if not auth_header:
            return None

        candidates = []
        used_token_prefix = False
        if " " in auth_header:
            prefix, rest = auth_header.split(" ", 1)
            if prefix == self.keyword:
                used_token_prefix = True
                candidates.append(rest.strip())

        candidates.append(auth_header)

        seen = set()
        for raw_key in candidates:
            if not raw_key or raw_key in seen:
                continue
            seen.add(raw_key)

            api_key = APIKey.authenticate(raw_key)
            if api_key is not None:
                return (api_key.user, api_key)

        if used_token_prefix:
            raise AuthenticationFailed("API Key inválida, inativa ou expirada.")

        return None