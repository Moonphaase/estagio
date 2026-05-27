from django.contrib import admin
from .models import Dataset, DatasetVersion, DatasetMetadata, Comment, DownloadLog, AuditLog


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display  = ["name", "owner", "category", "visibility", "status", "created_at"]
    list_filter   = ["visibility", "status", "category"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(DatasetVersion)
class DatasetVersionAdmin(admin.ModelAdmin):
    list_display = ["dataset", "version", "is_latest", "file_type", "file_size", "created_at"]
    list_filter  = ["is_latest", "file_type"]


@admin.register(DatasetMetadata)
class DatasetMetadataAdmin(admin.ModelAdmin):
    list_display = ["dataset", "source", "license", "language", "updated_at"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["dataset", "author", "created_at"]


@admin.register(DownloadLog)
class DownloadLogAdmin(admin.ModelAdmin):
    list_display    = ["dataset", "version", "user", "ip_address", "downloaded_at"]
    list_filter     = ["downloaded_at", "dataset"]
    search_fields   = ["dataset__name", "user__email", "ip_address"]
    readonly_fields = ["dataset", "version", "user", "ip_address", "downloaded_at"]

    def has_add_permission(self, request):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display    = ["timestamp", "user", "action", "resource", "resource_id", "description", "ip_address"]
    list_filter     = ["action", "resource", "timestamp"]
    search_fields   = ["user__email", "description", "ip_address"]
    readonly_fields = ["user", "action", "resource", "resource_id", "description", "changes", "ip_address", "timestamp"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False