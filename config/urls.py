from django.contrib import admin
from django.urls import path, include
from rest_framework_nested import routers

from categories.views import CategoryViewSet
from datasets.views   import DatasetViewSet, DatasetVersionViewSet

# ── router principal ──────────────────────────────────────────────────────────
router = routers.SimpleRouter()  # ← SimpleRouter em vez de DefaultRouter
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
    path("",          include("frontend.urls")),
]