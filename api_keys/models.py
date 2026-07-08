import secrets
import hashlib
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class APIKey(models.Model):
    PERMISSION_CHOICES = [
        ('read', 'Read Only'),
        ('write', 'Read & Write'),
        ('full', 'Full Access'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField(max_length=100)  # ex: "App móvel", "Script Python"
    key_full = models.CharField(max_length=128, blank=True)
    key_prefix = models.CharField(max_length=8, unique=True)   # primeiros 8 chars (visível)
    key_hash = models.CharField(max_length=64, unique=True)    # SHA-256 da chave completa
    permissions = models.CharField(max_length=10, choices=PERMISSION_CHOICES, default='read')
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)   # None = nunca expira
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.key_prefix}****) — {self.user.username}"

    @classmethod
    def generate(cls, user, name, permissions='read', expires_at=None):
        """Cria uma nova API key. Devolve (instância, chave_completa)."""
        raw_key = secrets.token_urlsafe(32)          # ex: "dK3mZ9..."  (visível só uma vez)
        prefix = raw_key[:8]
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        instance = cls.objects.create(
            user=user,
            name=name,
            key_full=raw_key,
            key_prefix=prefix,
            key_hash=key_hash,
            permissions=permissions,
            expires_at=expires_at,
        )
        return instance, raw_key   # raw_key mostrado só uma vez ao utilizador

    @classmethod
    def authenticate(cls, raw_key):
        """Valida uma chave recebida no header. Devolve APIKey ou None."""
        from django.utils import timezone
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        try:
            api_key = cls.objects.select_related('user').get(
                key_hash=key_hash,
                is_active=True,
            )
        except cls.DoesNotExist:
            return None

        if api_key.expires_at and api_key.expires_at < timezone.now():
            return None

        # Atualiza last_used sem guardar o objeto inteiro
        cls.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())
        return api_key