from rest_framework import authentication, exceptions
from django.utils import timezone
from datasets.models import APIKey

class APIKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        # A API do DRF espera o header 'Authorization'
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return None
        
        # Aceita "Token <chave>" ou "Bearer <chave>"
        parts = auth_header.split()
        if len(parts) != 2:
            return None
            
        # RESTRIÇÃO: Apenas métodos GET são permitidos com API Key
        if request.method != 'GET':
            raise exceptions.PermissionDenied('As chaves de API apenas permitem operações de leitura (GET).')
        
        key = parts[1]
        
        try:
            api_key = APIKey.objects.get(key_full=key)
        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed('Chave inválida.')

        if api_key.expires_at and api_key.expires_at < timezone.now().date():
            raise exceptions.AuthenticationFailed('Esta chave expirou.')

        return (api_key.user, api_key)