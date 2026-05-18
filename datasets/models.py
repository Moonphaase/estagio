from django.conf import settings
from django.db import models
from django.utils.text import slugify

from categories.models import Category


class Dataset(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC   = "public",   "Público"
        PRIVATE  = "private",  "Privado"
        INTERNAL = "internal", "Interno"

    class Status(models.TextChoices):
        DRAFT     = "draft",     "Rascunho"
        PUBLISHED = "published", "Publicado"
        ARCHIVED  = "archived",  "Arquivado"

    # ── campos originais ──────────────────────────────────────────────────────
    name        = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category    = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="datasets"
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    # ── campos novos ──────────────────────────────────────────────────────────
    slug       = models.SlugField(max_length=255, unique=True, blank=True)
    owner      = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="datasets"
    )
    visibility = models.CharField(
        max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC
    )
    status     = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT
    )

    class Meta:
        verbose_name = "Dataset"
        verbose_name_plural = "Datasets"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class DatasetVersion(models.Model):
    dataset     = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="versions"
    )
    version     = models.CharField(max_length=50)          # ex: "1.0.0"
    file        = models.FileField(upload_to="dataset_versions/")
    notes       = models.TextField(blank=True)             # release notes
    created_at  = models.DateTimeField(auto_now_add=True)
    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="dataset_versions"
    )

    class Meta:
        verbose_name = "Versão do Dataset"
        verbose_name_plural = "Versões do Dataset"
        ordering = ["-created_at"]
        unique_together = [("dataset", "version")]

    def __str__(self):
        return f"{self.dataset.name} — v{self.version}"

class DatasetMetadata(models.Model):
    dataset     = models.OneToOneField(
        Dataset, on_delete=models.CASCADE, related_name="metadata"
    )
    source      = models.URLField(blank=True)              # URL de origem
    license     = models.CharField(max_length=100, blank=True)  # ex: "CC BY 4.0"
    tags        = models.JSONField(default=list, blank=True)
    language    = models.CharField(max_length=50, blank=True)
    size_bytes  = models.BigIntegerField(null=True, blank=True)
    num_records = models.PositiveIntegerField(null=True, blank=True)
    extra       = models.JSONField(default=dict, blank=True)   # campo livre
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Metadados do Dataset"

    def __str__(self):
        return f"Metadados — {self.dataset.name}"
