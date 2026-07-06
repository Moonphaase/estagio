from rest_framework import authentication, exceptions
from django.utils import timezone
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
        if api_key.expires_at and api_key.expires_at < timezone.now().date():
            raise exceptions.AuthenticationFailed('Esta chave de API expirou.')
            
        # 3. Verifica se o utilizador está ativo (IMPORTANTE)
        if not api_key.user.is_active:
            raise exceptions.AuthenticationFailed('Utilizador associado à chave está inativo.')

        # Retorna o tuplo (user, auth)
        return (api_key.user, api_key)