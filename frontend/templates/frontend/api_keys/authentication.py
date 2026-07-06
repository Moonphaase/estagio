from rest_framework import authentication, exceptions
from django.utils import timezone
from datasets.models import APIKey

class APIKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION')
        
        # Se não há header, não tenta autenticar por aqui
        if not auth:
            return None
            
        # Extrai a chave (exemplo: "Token 123")
        try:
            key = auth.split(' ')[1]
        except IndexError:
            raise exceptions.AuthenticationFailed('Formato de autorização inválido.')

        # Tenta buscar a chave
        try:
            api_key = APIKey.objects.get(key_full=key)
        except APIKey.DoesNotExist:
            # AQUI ESTÁ O ERRO: Se a chave "1" não existe, o sistema TEM de parar aqui
            raise exceptions.AuthenticationFailed('Chave inexistente.')

        # Verificação de expiração
        if api_key.expires_at and api_key.expires_at < timezone.now().date():
            raise exceptions.AuthenticationFailed('Esta chave expirou.')

        return (api_key.user, api_key)