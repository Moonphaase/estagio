from rest_framework import authentication, exceptions
from django.utils import timezone
from datasets.models import APIKey

class APIKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        # DEBUG: Ponto de interrupção forçado para testar se a classe é chamada
        raise Exception("O Django chamou a classe APIKeyAuthentication!")

        auth = request.META.get('HTTP_AUTHORIZATION')
        if not auth:
            return None 

        try:
            key = auth.split(' ')[1]
        except IndexError:
            return None

        try:
            api_key = APIKey.objects.get(key_full=key)
        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed('Chave inválida')

        if api_key.expires_at and api_key.expires_at <= timezone.now().date():
            raise exceptions.AuthenticationFailed('Esta chave expirou.')

        return (api_key.user, api_key)