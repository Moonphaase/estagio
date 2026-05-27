from django.urls import path
from django.shortcuts import redirect
from . import views

urlpatterns = [
    path('', lambda request: redirect('login')),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('datasets/', views.datasets, name='datasets'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('datasets/create/', views.dataset_create, name='dataset_create'),
    path('datasets/<int:id>/', views.dataset_detail, name='dataset_detail'),
    path('categories/', views.categories, name='categories'),
    path('categories/create/', views.category_create, name='category_create'),
    path('profile/', views.profile, name='profile'),
    path('datasets/<int:id>/edit/', views.dataset_edit, name='dataset_edit'),
    path('datasets/<int:id>/versions/create/', views.version_create, name='version_create'),
    path('datasets/<int:id>/versions/', views.dataset_versions, name='dataset_versions'),
    path('datasets/<int:id>/versions/<int:version_id>/delete/', views.version_delete, name='version_delete'),
    path('logout/', views.logout_view, name='logout'),
    path('datasets/<int:id>/delete/', views.dataset_delete, name='dataset_delete'),
    path('users/', views.users, name='users'),
    path('users/<int:id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:id>/delete/', views.user_delete, name='user_delete'),
    path('auditoria/', views.auditoria, name='auditoria'),
    path('datasets/<int:id>/stats/', views.dataset_stats, name='dataset_stats'),
    path('datasets/<int:id>/versions/<int:version_id>/download/', views.version_download, name='version_download'),
]