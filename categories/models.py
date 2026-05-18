from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name        = models.CharField(max_length=255, unique=True)
    slug        = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name