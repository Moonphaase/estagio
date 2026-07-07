from rest_framework import authentication, exceptions
from django.utils import timezone
import logging

# Cria um logger para podermos ver o que se passa no Railway
logger = logging.getLogger(__name__)

from datasets.models import APIKey

class APIKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION')
        
        # 1. Se não houver header, permite que o DRF tente JWT ou Session
        if not auth or not auth.startswith('Token '):
            return None

        key = auth.split(' ')[1]

        try:
            api_key = APIKey.objects.select_related('user').get(key_full=key)
        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed('Chave de API inválida.')

        # 2. Verifica se a chave expirou
        # Log para depuração: verás isto nos logs do Railway
        current_date = timezone.now().date()
        logger.info(f"DEBUG AUTH: Chave={key[:5]}... Expira em={api_key.expires_at}, Data Atual={current_date}")

        if api_key.expires_at and api_key.expires_at < current_date:
            logger.warning(f"DEBUG AUTH: Bloqueando chave expirada {key[:5]}...")
            raise exceptions.AuthenticationFailed('Esta chave de API expirou.')
            
        # 3. Verifica se o utilizador está ativo
        if not api_key.user.is_active:
            raise exceptions.AuthenticationFailed('Utilizador associado à chave está inativo.')

        # Retorna o tuplo (user, auth)
        return (api_key.user, api_key)