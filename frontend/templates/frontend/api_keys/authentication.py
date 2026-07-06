from rest_framework import authentication, exceptions
from django.utils import timezone
from datasets.models import APIKey

class APIKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        # Procura o token no header Authorization
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None

        # Espera o formato "Token <chave>"
        if ' ' not in auth_header:
            return None
        
        _, key = auth_header.split(' ', 1)

        try:
            api_key_obj = APIKey.objects.get(key_full=key)
        except APIKey.DoesNotExist:
            return None # Retorna None para tentar o próximo método de autenticação

        # VERIFICAÇÃO RIGOROSA:
        # Se expires_at existe e é anterior a hoje, bloqueia acesso imediatamente
        if api_key_obj.expires_at and api_key_obj.expires_at < timezone.now().date():
            raise exceptions.AuthenticationFailed('Esta chave expirou.')

        return (api_key_obj.user, api_key_obj)