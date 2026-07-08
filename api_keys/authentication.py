from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from datasets.models import ApiKey


class ApiKeyAuthentication(BaseAuthentication):
    keyword = "Api-Key"

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None  # sem header -> AnonymousUser (a permission class é que bloqueia depois)

        try:
            prefix, key = auth_header.split(" ", 1)
        except ValueError:
            raise AuthenticationFailed("Formato inválido. Use: Authorization: Api-Key <chave>")

        if prefix != self.keyword:
            return None

        try:
            api_key = ApiKey.objects.get(key_full=key)
        except ApiKey.DoesNotExist:
            raise AuthenticationFailed("API Key inválida.")

        # Validar expiração diretamente no pedido, não depender do cron do painel
        if api_key.expires_at and api_key.expires_at < timezone.now():
            if api_key.is_active:
                api_key.is_active = False
                api_key.save(update_fields=["is_active"])
            raise AuthenticationFailed("API Key expirada.")

        if not api_key.is_active:
            raise AuthenticationFailed("API Key inativa.")

        return (api_key.user, api_key)