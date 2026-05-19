from django.contrib import admin
from .models import Dataset, DatasetVersion, DatasetMetadata


class MetadataInline(admin.StackedInline):
    model = DatasetMetadata
    extra = 0


class VersionInline(admin.TabularInline):
    model = DatasetVersion
    extra = 0
    readonly_fields = ["file_size", "file_type", "checksum", "is_latest", "created_at"]


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    inlines = [MetadataInline, VersionInline]
    list_display  = ("name", "owner", "category", "visibility", "status", "created_at")
    list_filter   = ("status", "visibility", "category")
    search_fields = ("name", "description", "owner__username")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at"]


@admin.register(DatasetVersion)
class DatasetVersionAdmin(admin.ModelAdmin):
    list_display  = ("dataset", "version", "is_latest", "file_type", "created_by", "created_at")
    list_filter   = ("is_latest", "file_type")
    readonly_fields = ["file_size", "file_type", "checksum", "is_latest", "created_at"]