from rest_framework import authentication, exceptions
from django.utils import timezone
from datasets.models import APIKey

class APIKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        # 1. Tenta obter a chave do Header Authorization
        auth = request.META.get('HTTP_AUTHORIZATION')
        if not auth:
            return None  # Passa para a próxima classe de autenticação (JWT ou Session)

        # 2. Extrai a chave (esperando formato "Token <chave>")
        try:
            key = auth.split(' ')[1]
        except IndexError:
            return None

        # 3. Busca no banco de dados
        try:
            api_key = APIKey.objects.get(key_full=key)
        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed('Chave inválida')

        # 4. A VERIFICAÇÃO DE EXPIRAÇÃO (Forçada)
        # Se expires_at existe e é uma data passada ou hoje, bloqueia
        # Nota: Ajusta para '<' se quiseres que "hoje" ainda seja válido.
        # Usa '<=' se "hoje" já deve ser considerado expirado.
        if api_key.expires_at and api_key.expires_at <= timezone.now().date():
            raise exceptions.AuthenticationFailed('Esta chave expirou.')

        # 5. Se passou, retorna o utilizador
        return (api_key.user, api_key)