from django.urls import path
from . import views

urlpatterns = [
    # ==========================================
    # ROTAS PRINCIPAIS E AUTENTICAÇÃO
    # ==========================================
    # 1. Página inicial (raiz) direciona para a lógica condicional (Sobre / Dashboard)
    path('', views.home, name='home'),
    
    # 2. Rota própria do Painel Geral
    path('dashboard/', views.dashboard, name='dashboard'),
    
    path('landing/', views.landing, name='landing'),
    path('about/', views.about, name='about'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile, name='profile'),

    # ==========================================
    # GESTÃO DE DATASETS (CRUD e Funcionalidades)
    # ==========================================
    path('datasets/', views.datasets, name='datasets'),
    path('datasets/create/', views.dataset_create, name='dataset_create'),
    path('datasets/<int:id>/', views.dataset_detail, name='dataset_detail'),
    path('datasets/<int:id>/edit/', views.dataset_edit, name='dataset_edit'),
    path('datasets/<int:id>/delete/', views.dataset_delete, name='dataset_delete'),
    path('datasets/<int:id>/favorite/', views.dataset_favorite, name='dataset_favorite'),
    path('datasets/<int:id>/stats/', views.dataset_stats, name='dataset_stats'),
    
    # Fluxo de Aprovação e Partilha de Datasets
    path('datasets/<int:id>/submit/', views.dataset_submit, name='dataset_submit'),
    path('datasets/<int:id>/approve/', views.dataset_approve, name='dataset_approve'),
    path('datasets/<int:id>/reject/', views.dataset_reject, name='dataset_reject'),
    path('datasets/<int:id>/share/', views.dataset_share, name='dataset_share'),
    path('datasets/<int:id>/share/remove/<int:share_id>/', views.dataset_share_remove, name='dataset_share_remove'),

    # ==========================================
    # VERSÕES DE DATASETS
    # ==========================================
    path('datasets/<int:id>/versions/', views.dataset_versions, name='dataset_versions'),
    path('datasets/<int:id>/versions/create/', views.version_create, name='version_create'),
    path('datasets/<int:id>/versions/<int:version_id>/delete/', views.version_delete, name='version_delete'),
    path('datasets/<int:id>/versions/<int:version_id>/download/', views.version_download, name='version_download'),

    # ==========================================
    # COMENTÁRIOS nos Datasets
    # ==========================================
    path('datasets/<int:id>/comments/create/', views.comment_create, name='comment_create'),
    path('datasets/<int:id>/comments/delete/<int:comment_id>/', views.comment_delete, name='comment_delete'),

    # ==========================================
    # CATEGORIAS
    # ==========================================
    path('categories/', views.categories, name='categories'),
    path('categories/create/', views.category_create, name='category_create'),

    # ==========================================
    # ADMINISTRAÇÃO, UTILIZADORES E AUDITORIA
    # ==========================================
    path('users/', views.users, name='users'),
    path('users/<int:id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:id>/delete/', views.user_delete, name='user_delete'),
    path('aprovacoes/', views.aprovacoes, name='aprovacoes'),
    path('auditoria/', views.auditoria, name='auditoria'),
]