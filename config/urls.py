from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_nested import routers

from categories.views import CategoryViewSet
from datasets.views   import DatasetViewSet, DatasetVersionViewSet

# ── router principal ──────────────────────────────────────────────────────────
router = routers.SimpleRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"datasets",   DatasetViewSet,  basename="dataset")

# ── router aninhado para versões ──────────────────────────────────────────────
datasets_router = routers.NestedSimpleRouter(router, r"datasets", lookup="dataset")
datasets_router.register(r"versions", DatasetVersionViewSet, basename="dataset-versions")

urlpatterns = [
    path("admin/",    admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/",      include(router.urls)),
    path("api/",      include(datasets_router.urls)),
    path("api-auth/", include("rest_framework.urls")),
    path("",          include("frontend.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)