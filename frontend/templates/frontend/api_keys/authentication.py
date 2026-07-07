from rest_framework import authentication, exceptions
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

from datasets.models import ApiKey

class APIKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        print("=== APIKeyAuthentication.authenticate() CHAMADO ===", flush=True)
        auth = request.META.get('HTTP_AUTHORIZATION')
        print(f"=== HTTP_AUTHORIZATION recebido: {auth} ===", flush=True)

        if not auth or not auth.startswith('Token '):
            print("=== SAIU: sem header ou formato errado ===", flush=True)
            return None

        key = auth.split(' ')[1]
        print(f"=== Key extraída: {key[:8]}... ===", flush=True)

        try:
            api_key = ApiKey.objects.select_related('user').get(key_full=key)
            print(f"=== Key encontrada na BD para user={api_key.user} ===", flush=True)
        except ApiKey.DoesNotExist:
            print("=== Key NÃO existe na BD ===", flush=True)
            raise exceptions.AuthenticationFailed('Chave de API inválida.')

        # expires_at é DateTimeField — comparar com timezone.now() diretamente
        logger.info(f"DEBUG AUTH: Chave={key[:5]}... Expira em={api_key.expires_at}, Agora={timezone.now()}")

        if api_key.expires_at and api_key.expires_at < timezone.now():
            logger.warning(f"DEBUG AUTH: Bloqueando chave expirada {key[:5]}...")
            raise exceptions.AuthenticationFailed('Esta chave de API expirou.')

        if not api_key.is_active:
            raise exceptions.AuthenticationFailed('Esta chave de API está inativa.')

        if not api_key.user.is_active:
            raise exceptions.AuthenticationFailed('Utilizador associado à chave está inativo.')

        return (api_key.user, api_key)