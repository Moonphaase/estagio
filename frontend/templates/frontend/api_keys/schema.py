from drf_spectacular.extensions import OpenApiAuthenticationExtension

class APIKeyAuthenticationExtension(OpenApiAuthenticationExtension):
    target_class = 'api_keys.authentication.APIKeyAuthentication'  # Caminho para a tua classe
    name = 'APIKeyAuthentication'  # Nome que aparecerá no Swagger

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': 'Formato: Token <sua_chave>'
        }