from rest_framework import authentication, exceptions
from django.utils import timezone
from datasets.models import APIKey

class APIKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None
        
        # Ajusta conforme o prefixo que usas (Token, Bearer, etc)
        # Se usas apenas a chave, remove o split
        if ' ' in auth_header:
            _, key = auth_header.split(' ', 1)
        else:
            key = auth_header

        try:
            api_key_obj = APIKey.objects.get(key_full=key)
            
            # DEBUG: Mostra o que está a acontecer no log do servidor
            hoje = timezone.now().date()
            print(f"DEBUG: Chave {api_key_obj.name} | Expira em: {api_key_obj.expires_at} | Hoje: {hoje}")
            
            if api_key_obj.expires_at and api_key_obj.expires_at < hoje:
                print("DEBUG: A chave está expirada! Disparando erro.")
                raise exceptions.AuthenticationFailed('Esta chave expirou.')
            
            return (api_key_obj.user, api_key_obj)
            
        except APIKey.DoesNotExist:
            return None