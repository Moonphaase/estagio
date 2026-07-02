from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_nested import routers
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from categories.views import CategoryViewSet
from datasets.views   import DatasetViewSet, DatasetVersionViewSet
from frontend import views  # Importa as views do frontend

# ── router principal ──────────────────────────────────────────────────────────
router = routers.SimpleRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"datasets",   DatasetViewSet,  basename="dataset")

# ── router aninhado para versões ──────────────────────────────────────────────
datasets_router = routers.NestedSimpleRouter(router, r"datasets", lookup="dataset")
datasets_router.register(r"versions", DatasetVersionViewSet, basename="dataset-versions")

urlpatterns = [
    path("admin/",     admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/",       include(router.urls)),
    path("api/",       include(datasets_router.urls)),
    path("api-auth/", include("rest_framework.urls")),
    
    # ── Frontend Rotas ────────────────────────────────────────────────────────
    path("",           include("frontend.urls")),
    
    # Rota personalizada para a gestão de chaves no frontend
    path('api-keys/', views.manage_api_keys, name='manage_api_keys'),
    
    # Rota para a API de chaves
    path('api/auth/api-keys/', views.manage_api_keys, name='manage_api_keys'),
    path('api/auth/api-keys/<int:id>/', views.manage_api_keys, name='manage_api_keys_delete'),

    # ── Documentação Swagger ──────────────────────────────────────────────────
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)