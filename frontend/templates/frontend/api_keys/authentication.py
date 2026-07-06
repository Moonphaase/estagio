from rest_framework import authentication, exceptions
from django.utils import timezone
from .models import APIKey # Certifica-te que este import aponta para o teu modelo

class APIKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        # Procura a chave no header Authorization
        auth = request.META.get('HTTP_AUTHORIZATION', '').split()
        
        if not auth or auth[0].lower() != 'token':
            return None

        if len(auth) == 1:
            raise exceptions.AuthenticationFailed('Cabeçalho de autenticação inválido. Falta o token.')
        elif len(auth) > 2:
            raise exceptions.AuthenticationFailed('Cabeçalho de autenticação inválido. Token de string de autenticação não deve conter espaços.')

        key = auth[1]

        try:
            api_key_obj = APIKey.objects.get(key_full=key)
        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed('Chave inválida.')

        # --- A VERIFICAÇÃO DE EXPIRAÇÃO ---
        # Se a chave tem uma data de expiração e ela é menor que a data de hoje, bloqueia o acesso
        if api_key_obj.expires_at and api_key_obj.expires_at < timezone.now().date():
            raise exceptions.AuthenticationFailed('Esta chave expirou.')

        return (api_key_obj.user, api_key_obj)