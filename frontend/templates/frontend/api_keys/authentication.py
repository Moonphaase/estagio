from rest_framework import authentication, exceptions
from django.utils import timezone
from datasets.models import APIKey

class APIKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION')
        
        # Se não há header, não tenta autenticar por aqui
        if not auth:
            return None
            
        # Tenta extrair a chave
        try:
            # Assume o formato "Token <chave>"
            key = auth.split(' ')[1]
        except IndexError:
            raise exceptions.AuthenticationFailed('Formato de autorização inválido.')

        try:
            api_key = APIKey.objects.get(key_full=key)
        except APIKey.DoesNotExist:
            # Se a chave não existe, bloqueia imediatamente
            raise exceptions.AuthenticationFailed('Chave inexistente.')

        # Verificação rigorosa de data
        hoje = timezone.now().date()
        if api_key.expires_at and api_key.expires_at < hoje:
            raise exceptions.AuthenticationFailed('Esta chave expirou.')

        return (api_key.user, api_key)