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
    name = models.CharField(max_length=100)
    key_full = models.CharField(max_length=64, unique=True)
    key_prefix = models.CharField(max_length=8, unique=True)
    key_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)
    permissions = models.CharField(max_length=10, choices=PERMISSION_CHOICES, default='read')
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.key_prefix}****) — {self.user.username}"

    @classmethod
    def generate(cls, user, name, permissions='read', expires_at=None):
        raw_key = secrets.token_urlsafe(32)
        prefix = raw_key[:8]
        instance = cls.objects.create(
            user=user,
            name=name,
            key_full=raw_key,
            key_prefix=prefix,
            key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
            permissions=permissions,
            expires_at=expires_at,
        )
        return instance, raw_key

    @classmethod
    def authenticate(cls, raw_key):
        from django.utils import timezone
        try:
            api_key = cls.objects.select_related('user').get(
                key_full=raw_key,
                is_active=True,
            )
        except cls.DoesNotExist:
            return None
        if api_key.expires_at and api_key.expires_at < timezone.now():
            return None
        cls.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())
        return api_key