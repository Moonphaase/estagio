from rest_framework import authentication, exceptions
from django.utils import timezone
from datasets.models import APIKey

class APIKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION')
        
        # Se não há header de autenticação, retorna None (para tentar JWT ou Session)
        if not auth or not auth.startswith('Token '):
            return None

        key = auth.split(' ')[1]

        try:
            api_key = APIKey.objects.get(key_full=key)
        except APIKey.DoesNotExist:
            # Se a chave foi enviada mas não existe no banco, bloqueia o acesso
            raise exceptions.AuthenticationFailed('Chave de API inválida.')

        # Verificação de Expiração
        if api_key.expires_at:
            # Compara se a data de expiração já passou
            if api_key.expires_at < timezone.now().date():
                raise exceptions.AuthenticationFailed('Esta chave de API expirou.')

        return (api_key.user, api_key)