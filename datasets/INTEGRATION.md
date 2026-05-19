# Integração da app `datasets` no projeto Django

## 1. Registar a app em `config/settings.py`

```python
INSTALLED_APPS = [
    ...
    'rest_framework',
    'rest_framework_simplejwt',
    'datasets',
    'categories',   # se existir como app separada; caso contrário o modelo Category está em datasets/
    ...
]

# Media files (uploads)
import os
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

## 2. Incluir as URLs em `config/urls.py`

```python
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('datasets.urls')),
    path('api/auth/', include('accounts.urls')),  # JWT auth
    ...
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

## 3. Criar e aplicar as migrações

```bash
python manage.py makemigrations datasets
python manage.py migrate
```

## 4. Endpoints disponíveis

| Método | URL | Descrição |
|--------|-----|-----------|
| GET | `/api/categories/` | Listar categorias |
| POST | `/api/categories/` | Criar categoria (admin) |
| GET/PUT/DELETE | `/api/categories/{id}/` | Gerir categoria |
| GET | `/api/datasets/` | Listar datasets (filtros: category, owner, visibility, status) |
| POST | `/api/datasets/` | Criar dataset |
| GET | `/api/datasets/{id}/` | Detalhe completo (com versões e metadados) |
| PUT/PATCH | `/api/datasets/{id}/` | Editar (dono ou admin) |
| DELETE | `/api/datasets/{id}/` | Apagar (dono ou admin) |
| GET | `/api/datasets/{id}/versions/` | Listar versões |
| POST | `/api/datasets/{id}/versions/` | Criar versão (com upload de ficheiro) |
| GET | `/api/datasets/{id}/versions/{vid}/` | Detalhe de versão |
| DELETE | `/api/datasets/{id}/versions/{vid}/` | Apagar versão |
| GET | `/api/datasets/{id}/versions/{vid}/download/` | Download de versão |
| GET | `/api/datasets/{id}/latest/download/` | Download da versão mais recente |

## 5. Filtros disponíveis em GET /api/datasets/

```
?category=saude          # filtra por slug da categoria
?owner=username          # filtra por username do dono
?visibility=public       # public / private / internal
?status=published        # draft / published / archived
?search=porto            # pesquisa em title, description, category
?ordering=-created_at    # ordenação
```

## 6. Exemplo de criação de versão (multipart/form-data)

```bash
curl -X POST /api/datasets/1/versions/ \
  -H "Authorization: Bearer <token>" \
  -F "version_number=1.0.0" \
  -F "title=Versão inicial" \
  -F "description=Dados de 2024" \
  -F "file=@dados.csv"
```

## 7. Estrutura de ficheiros gerada

```
media/
└── datasets/
    └── {dataset_id}/
        └── {version_number}/
            └── ficheiro.csv
```

## 8. Ficheiros da app

```
datasets/
├── __init__.py
├── apps.py
├── models.py       ← Dataset, DatasetVersion, DatasetMetadata, Category
├── serializers.py  ← Serializers para os 4 modelos
├── views.py        ← ViewSets com CRUD, versões, download, permissões
├── permissions.py  ← IsOwnerOrAdmin, IsAdminOrReadOnly
├── urls.py         ← Router + rotas
└── admin.py        ← Registo no Django Admin
```