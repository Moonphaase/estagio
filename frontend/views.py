import csv
import io
import logging
import json
import secrets

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Q
from django.http import FileResponse, JsonResponse
from categories.models import Category
from datasets.models import Dataset, DatasetVersion, DownloadLog, AuditLog, DatasetFavorite, DatasetShare, DatasetMetadata
from datasets.audit import audit, audit_dataset_changes
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password
from api_keys.models import APIKey
from datetime import datetime, timezone as dt_timezone
from django.utils import timezone

logger = logging.getLogger('accounts')


def dashboard(request):
    if request.user.is_authenticated:
        is_guest = False
        if request.user.is_staff:
            recent_datasets = Dataset.objects.all().order_by('-created_at')[:5]
            total_datasets  = Dataset.objects.count()
            total_versions  = DatasetVersion.objects.count()
        else:
            # ALTERADO: Garante que vês os teus próprios OU os públicos de outros que já foram publicados
            qs = Dataset.objects.filter(
                Q(owner=request.user) | Q(visibility='public', status='published')
            )
            recent_datasets = qs.order_by('-created_at')[:5]
            total_datasets  = qs.count()
            total_versions  = DatasetVersion.objects.filter(dataset__in=qs).count()
        my_datasets = Dataset.objects.filter(owner=request.user).count()
    else:
        # Visitante não logado: Só vê o que é Público E está Publicado
        is_guest = True
        qs = Dataset.objects.filter(visibility='public', status='published')
        recent_datasets = qs.order_by('-created_at')[:5]
        total_datasets  = qs.count()
        total_versions  = DatasetVersion.objects.filter(dataset__in=qs).count()
        my_datasets = 0

    total_categories = Category.objects.count()
    return render(request, 'frontend/dashboard.html', {
        'recent_datasets':  recent_datasets,
        'total_datasets':   total_datasets,
        'total_categories': total_categories,
        'total_versions':   total_versions,
        'my_datasets':      my_datasets,
        'is_guest':         is_guest,
    })


def datasets(request):
    search            = request.GET.get('search', '').strip()
    category_filter   = request.GET.get('category', '')
    visibility_filter = request.GET.get('visibility', '')
    status_filter     = request.GET.get('status', '')
    favorites_filter  = request.GET.get('favorites', '')

    if request.user.is_authenticated:
        is_guest = False
        if request.user.is_staff:
            qs = Dataset.objects.all()
        else:
            qs = Dataset.objects.filter(
                Q(visibility='public') | Q(owner=request.user)
            )
    else:
        is_guest = True
        # Visitante não logado: Só vê o que é Público E está Publicado
        qs = Dataset.objects.filter(visibility='public', status='published')

    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
    if category_filter:
        qs = qs.filter(category__slug=category_filter)
    if visibility_filter:
        qs = qs.filter(visibility=visibility_filter)
    if status_filter:
        qs = qs.filter(status=status_filter)
        
    if favorites_filter:
        if request.user.is_authenticated:
            favorited_ids = DatasetFavorite.objects.filter(
                user=request.user
            ).values_list('dataset_id', flat=True)
            qs = qs.filter(id__in=favorited_ids)
        else:
            qs = qs.none()

    qs         = qs.order_by('-created_at')
    categories = Category.objects.all()
    return render(request, 'frontend/datasets.html', {
        'datasets':          qs,
        'categories':        categories,
        'search':            search,
        'category_filter':   category_filter,
        'visibility_filter': visibility_filter,
        'status_filter':     status_filter,
        'favorites_filter':  favorites_filter,
        'is_guest':          is_guest,
    })

@login_required
def manage_api_keys(request):
    return render(request, 'frontend/api_keys/manage.html')

@login_required
def api_keys_api(request, id=None):
    if request.method == "GET":
        # Desativa automaticamente chaves expiradas
        APIKey.objects.filter(expires_at__lt=timezone.now(), is_active=True).update(is_active=False)
        keys = APIKey.objects.filter(user=request.user).values(
            'id', 'name', 'key_full', 'expires_at', 'is_active'
        )
        return JsonResponse(list(keys), safe=False)

    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            expiry_str = data.get('expires_at')

            if not expiry_str:
                expiry_date = timezone.now() + timezone.timedelta(days=30)
            else:
                naive_dt = datetime.strptime(expiry_str, '%Y-%m-%d')
                expiry_date = timezone.make_aware(naive_dt)

            instance, raw_key = APIKey.generate(
                user=request.user,
                name=data.get('name', 'Nova Chave'),
                permissions=data.get('permissions', 'read'),
                expires_at=expiry_date,
            )
            return JsonResponse({
                'message': 'Chave gerada com sucesso!',
                'key': raw_key,  # mostrada uma única vez ao utilizador
            }, status=201)
        except Exception as e:
            print(f"Erro na geração: {e}")
            return JsonResponse({'error': str(e)}, status=400)

    elif request.method == "DELETE" and id:
        APIKey.objects.filter(id=id, user=request.user).delete()
        return JsonResponse({'message': 'Chave eliminada'}, status=200)

    return JsonResponse({'error': 'Método inválido'}, status=405)

def login_view(request):
    if request.method == 'POST':
        email    = request.POST.get('email')
        password = request.POST.get('password')
        user     = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            logger.info(f'Login: {email}')
            return redirect('dashboard')
        else:
            logger.warning(f'Login falhado: {email}')
            return render(request, 'frontend/login.html', {'error': 'Email ou password incorretos ou conta pendente de aprovação.'})
    return render(request, 'frontend/login.html')


def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email    = request.POST.get('email')
        password = request.POST.get('password')

        from django.contrib.auth import get_user_model
        User = get_user_model()

        if User.objects.filter(username=username).exists():
            return render(request, 'frontend/register.html', {'error': 'Nome de utilizador já existe'})
        if User.objects.filter(email=email).exists():
            return render(request, 'frontend/register.html', {'error': 'Email já está registado'})

        user = User.objects.create_user(username=username, email=email, password=password)
        user.is_active = False
        user.save()
        
        logger.info(f'Utilizador registado (aguardando aprovação): {email}')
        messages.success(request, 'Conta criada com sucesso! O seu acesso aguarda aprovação por um administrador.')
        return redirect('login')

    return render(request, 'frontend/register.html')


@login_required
def comment_create(request, id):
    dataset = get_object_or_404(Dataset, id=id)
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            from datasets.models import Comment
            Comment.objects.create(dataset=dataset, author=request.user, content=content)
            messages.success(request, 'Comentário adicionado.')
    return redirect('dataset_detail', dataset.id)


@login_required
def comment_delete(request, id, comment_id):
    from datasets.models import Comment
    dataset = get_object_or_404(Dataset, id=id)
    comment = get_object_or_404(Comment, id=comment_id, dataset=dataset)

    if comment.author != request.user and not request.user.is_staff:
        messages.error(request, 'Não tens permissão para apagar este comentário.')
        return redirect('dataset_detail', dataset.id)

    if request.method == 'POST':
        comment.delete()
        messages.success(request, 'Comentário apagado.')

    return redirect('dataset_detail', dataset.id)


def dataset_detail(request, id):
    dataset = get_object_or_404(Dataset, id=id)
    
    if request.user.is_authenticated:
        is_guest = False
        has_share = DatasetShare.objects.filter(dataset=dataset, shared_with=request.user).exists()
        is_owner = dataset.owner == request.user
        is_favorited = DatasetFavorite.objects.filter(user=request.user, dataset=dataset).exists()

        if dataset.visibility == 'private' and dataset.owner != request.user and not request.user.is_staff and not has_share:
            messages.error(request, 'Não tens permissão para ver este dataset.')
            return redirect('datasets')
    else:
        is_guest = True
        is_owner = False
        is_favorited = False
        # Visitante não pode ver datasets privados nem datasets que não estejam publicados
        if dataset.visibility == 'private' or dataset.status != 'published':
            messages.error(request, 'Este dataset não está disponível publicamente.')
            return redirect('dashboard')

    versions = DatasetVersion.objects.filter(dataset=dataset).order_by('-created_at')

    from datasets.models import Comment
    comments = Comment.objects.filter(dataset=dataset).select_related('author').order_by('created_at')

    tags = []
    if hasattr(dataset, 'metadata') and dataset.metadata:
        tags = dataset.metadata.tags or []

    csv_headers = []
    csv_rows    = []
    latest      = versions.filter(is_latest=True).first()
    if latest and latest.file_type == 'csv':
        try:
            with latest.file.open('r') as f:
                content = f.read()
                if isinstance(content, bytes):
                    content = content.decode('utf-8', errors='replace')
                reader = csv.reader(io.StringIO(content))
                rows   = list(reader)
                if rows:
                    csv_headers = rows[0]
                    csv_rows    = rows[1:6]
        except Exception:
            pass

    return render(request, 'frontend/dataset_detail.html', {
        'dataset':      dataset,
        'versions':     versions,
        'is_owner':     is_owner,
        'is_favorited': is_favorited,
        'tags':         tags,
        'comments':     comments,
        'csv_headers':  csv_headers,
        'csv_rows':     csv_rows,
        'is_guest':     is_guest,
    })


@login_required
def dataset_favorite(request, id):
    dataset  = get_object_or_404(Dataset, id=id)
    favorite, created = DatasetFavorite.objects.get_or_create(user=request.user, dataset=dataset)
    if not created:
        favorite.delete()
        return JsonResponse({'is_favorited': False})
    return JsonResponse({'is_favorited': True})


@login_required
def dataset_create(request):
    if request.method == 'POST':
        name        = request.POST.get('name')
        description = request.POST.get('description')
        category_id = request.POST.get('category')
        visibility  = request.POST.get('visibility', 'public')
        status_val  = request.POST.get('status', 'draft')

        category = None
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                pass

        dataset = Dataset.objects.create(
            name=name, description=description, category=category,
            owner=request.user, visibility=visibility, status=status_val
        )

        tags_raw = request.POST.get('tags', '')
        tags     = [t.strip() for t in tags_raw.split(',') if t.strip()]
        if tags:
            metadata, _ = DatasetMetadata.objects.get_or_create(dataset=dataset)
            metadata.tags = tags
            metadata.save()

        audit(request, "create", "dataset", dataset.id, f"Dataset '{dataset.name}' criado")
        logger.info(f'Dataset criado: "{dataset.name}" por {request.user.email}')
        messages.success(request, 'Dataset criado com sucesso!')
        return redirect('dataset_detail', dataset.id)

    categories = Category.objects.all()
    return render(request, 'frontend/dataset_create.html', {'categories': categories})


def categories(request):
    search = request.GET.get('search', '').strip()
    qs     = Category.objects.all()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
    return render(request, 'frontend/categories.html', {
        'categories': qs,
        'search':     search,
        'is_guest':   not request.user.is_authenticated,
    })


@login_required
def dataset_edit(request, id):
    dataset = get_object_or_404(Dataset, id=id)

    if dataset.owner != request.user and not request.user.is_staff:
        messages.error(request, 'Não tens permissão para editar este dataset.')
        return redirect('dataset_detail', dataset.id)

    if request.method == 'POST':
        before = {
            "name":        dataset.name,
            "description": dataset.description,
            "visibility":  dataset.visibility,
            "status":      dataset.status,
            "category":    str(dataset.category),
        }

        dataset.name        = request.POST.get('name')
        dataset.description = request.POST.get('description')
        category_id         = request.POST.get('category')
        dataset.visibility  = request.POST.get('visibility', 'public')
        dataset.status      = request.POST.get('status', 'draft')

        if category_id:
            try:
                dataset.category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                dataset.category = None
        else:
            dataset.category = None

        dataset.save()

        tags_raw = request.POST.get('tags', '')
        tags     = [t.strip() for t in tags_raw.split(',') if t.strip()]
        metadata, _ = DatasetMetadata.objects.get_or_create(dataset=dataset)
        metadata.tags = tags
        metadata.save()

        after = {
            "name":        dataset.name,
            "description": dataset.description,
            "visibility":  dataset.visibility,
            "status":      dataset.status,
            "category":    str(dataset.category),
        }
        changes = audit_dataset_changes(before, after)
        audit(request, "update", "dataset", dataset.id, f"Dataset '{dataset.name}' editado", changes=changes)
        logger.info(f'Dataset editado: "{dataset.name}" por {request.user.email}')
        messages.success(request, 'Dataset updated com sucesso!')
        return redirect('dataset_detail', dataset.id)

    tags_list = []
    tags_str  = ''
    if hasattr(dataset, 'metadata') and dataset.metadata:
        tags_list = dataset.metadata.tags or []
        tags_str  = ', '.join(tags_list)

    categories = Category.objects.all()
    return render(request, 'frontend/dataset_edit.html', {
        'dataset':    dataset,
        'categories': categories,
        'tags_list':  tags_list,
        'tags_str':   tags_str,
    })


@login_required
def dataset_versions(request, id):
    dataset = get_object_or_404(Dataset, id=id)

    if dataset.visibility == 'private' and dataset.owner != request.user and not request.user.is_staff:
        messages.error(request, 'Não tens permissão para ver este dataset.')
        return redirect('datasets')

    versions = DatasetVersion.objects.filter(dataset=dataset).order_by('-created_at')
    is_owner = dataset.owner == request.user
    return render(request, 'frontend/dataset_versions.html', {
        'dataset':  dataset,
        'versions': versions,
        'is_owner': is_owner,
    })


def logout_view(request):
    logger.info(f'Logout: {request.user.email if request.user.is_authenticated else "anonimo"}')
    logout(request)
    return redirect('home') # Alterado de 'dashboard' para 'home'


@login_required
def dataset_delete(request, id):
    dataset = get_object_or_404(Dataset, id=id)

    if dataset.owner != request.user and not request.user.is_staff:
        messages.error(request, 'Não tens permissão para apagar este dataset.')
        return redirect('dataset_detail', dataset.id)

    if request.method == 'POST':
        audit(request, "delete", "dataset", dataset.id, f"Dataset '{dataset.name}' apagado")
        logger.info(f'Dataset apagado: "{dataset.name}" por {request.user.email}')
        dataset.delete()
    return redirect('datasets')


@login_required
def category_create(request):
    if not request.user.is_staff:
        messages.error(request, 'Não tens permissão para criar categorias.')
        return redirect('categories')

    if request.method == 'POST':
        name        = request.POST.get('name')
        slug        = request.POST.get('slug')
        description = request.POST.get('description')

        if Category.objects.filter(name=name).exists():
            return render(request, 'frontend/category_create.html', {
                'error': f'Já existe uma categoria com o nome "{name}".'
            })
        if Category.objects.filter(slug=slug).exists():
            return render(request, 'frontend/category_create.html', {
                'error': f'Já existe uma categoria com o slug "{slug}".'
            })

        if name and slug:
            cat = Category.objects.create(name=name, slug=slug, description=description)
            audit(request, "create", "category", cat.id, f"Categoria '{name}' criada")
            logger.info(f'Categoria criada: "{name}" por {request.user.email}')
            messages.success(request, 'Categoria criada com sucesso!')
            return redirect('categories')

    return render(request, 'frontend/category_create.html')


@login_required
def version_create(request, id):
    dataset = get_object_or_404(Dataset, id=id)

    if dataset.owner != request.user and not request.user.is_staff:
        messages.error(request, 'Não tens permissão para criar versões neste dataset.')
        return redirect('dataset_detail', dataset.id)

    if request.method == 'POST':
        version = request.POST.get('version')
        title   = request.POST.get('title')
        notes   = request.POST.get('notes')
        file    = request.FILES.get('file')

        if not version or not file:
            return render(request, 'frontend/version_create.html', {
                'dataset': dataset, 'error': 'Versão e ficheiro são obrigatórios.'
            })

        if DatasetVersion.objects.filter(dataset=dataset, version=version).exists():
            return render(request, 'frontend/version_create.html', {
                'dataset': dataset, 'error': f'Já existe a versão {version} neste dataset.'
            })

        from core.helpers import validate_file_extension, validate_file_size, generate_checksum, dataset_upload_path
        from django.core.exceptions import ValidationError

        try:
            validate_file_extension(file)
            validate_file_size(file)
        except ValidationError as e:
            return render(request, 'frontend/version_create.html', {
                'dataset': dataset, 'error': str(e.message)
            })

        checksum = generate_checksum(file)
        if dataset.versions.filter(checksum=checksum).exists():
            return render(request, 'frontend/version_create.html', {
                'dataset': dataset, 'error': 'Este ficheiro já foi enviado numa versão anterior.'
            })

        file.name = dataset_upload_path(dataset.id, version, file.name)

        DatasetVersion.objects.filter(dataset=dataset, is_latest=True).update(is_latest=False)
        v = DatasetVersion.objects.create(
            dataset=dataset, version=version, title=title,
            notes=notes, file=file, created_by=request.user, is_latest=True
        )
        audit(request, "create", "version", v.id,
              f"Versão '{version}' criada no dataset '{dataset.name}'")
        logger.info(f'Versão criada: "{dataset.name}" v{version} por {request.user.email}')
        messages.success(request, f'Versão {version} criada com sucesso!')
        return redirect('dataset_versions', dataset.id)

    return render(request, 'frontend/version_create.html', {'dataset': dataset})


@login_required
def profile(request):
    if request.method == 'POST':
        # Vamos verificar qual formulário foi enviado através do campo 'action'
        action = request.POST.get('action')

        if action == 'update_profile':
            # Atualização de dados pessoais
            user = request.user
            user.username = request.POST.get('username', user.username)
            user.email = request.POST.get('email', user.email)
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.save()
            messages.success(request, 'Informações pessoais atualizadas com sucesso!')

        elif action == 'change_password':
            # Alteração de password
            current = request.POST.get('current_password')
            new = request.POST.get('new_password')
            confirm = request.POST.get('confirm_password')

            if not request.user.check_password(current):
                messages.error(request, 'A password atual está incorreta.')
            elif new != confirm:
                messages.error(request, 'As novas passwords não coincidem.')
            elif len(new) < 6:
                messages.error(request, 'A nova password deve ter pelo menos 6 caracteres.')
            else:
                request.user.set_password(new)
                request.user.save()
                # É importante fazer o login novamente após mudar a password
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password alterada com sucesso!')

        return redirect('profile')

    return render(request, 'frontend/profile.html')


@login_required
def users(request):
    if not request.user.is_staff:
        messages.error(request, 'Não tens permissão para ver esta página.')
        return redirect('dashboard')
    from django.contrib.auth import get_user_model
    User      = get_user_model()
    all_users = User.objects.all().order_by('date_joined')
    return render(request, 'frontend/users.html', {'users': all_users})


@login_required
def user_edit(request, id):
    if not request.user.is_staff:
        messages.error(request, 'Não tens permissão para editar utilizadores.')
        return redirect('dashboard')
    from django.contrib.auth import get_user_model
    User        = get_user_model()
    edited_user = get_object_or_404(User, id=id)

    if request.method == 'POST':
        before = {
            "username":  edited_user.username,
            "email":     edited_user.email,
            "is_staff":  edited_user.is_staff,
            "is_active": edited_user.is_active,
        }
        edited_user.username   = request.POST.get('username')
        edited_user.email      = request.POST.get('email')
        edited_user.first_name = request.POST.get('first_name')
        edited_user.last_name  = request.POST.get('last_name')
        edited_user.is_staff   = request.POST.get('is_staff') == 'on'
        edited_user.is_active  = request.POST.get('is_active') == 'on'
        edited_user.save()
        after = {
            "username":  edited_user.username,
            "email":     edited_user.email,
            "is_staff":  edited_user.is_staff,
            "is_active": edited_user.is_active,
        }
        changes = audit_dataset_changes(before, after)
        audit(request, "update", "user", edited_user.id,
              f"Utilizador '{edited_user.username}' editado", changes=changes)
        messages.success(request, 'Utilizador atualizado com sucesso!')
        return redirect('users')

    return render(request, 'frontend/user_edit.html', {'edited_user': edited_user})


@login_required
def user_delete(request, id):
    if not request.user.is_staff:
        messages.error(request, 'Não tens permissão para apagar utilizadores.')
        return redirect('dashboard')
    from django.contrib.auth import get_user_model
    User        = get_user_model()
    edited_user = get_object_or_404(User, id=id)
    if request.method == 'POST':
        audit(request, "delete", "user", edited_user.id,
              f"Utilizador '{edited_user.username}' apagado")
        edited_user.delete()
        messages.success(request, 'Utilizador apagado com sucesso.')
    return redirect('users')


@login_required
def version_delete(request, id, version_id):
    dataset = get_object_or_404(Dataset, id=id)
    version = get_object_or_404(DatasetVersion, id=version_id, dataset=dataset)

    if dataset.owner != request.user and not request.user.is_staff:
        messages.error(request, 'Não tens permissão para apagar esta versão.')
        return redirect('dataset_versions', dataset.id)

    if request.method == 'POST':
        was_latest = version.is_latest
        audit(request, "delete", "version", version.id,
              f"Versão '{version.version}' apagada do dataset '{dataset.name}'")
        logger.info(f'Versão apagada: "{dataset.name}" v{version.version} por {request.user.email}')
        if version.file:
            version.file.delete(save=False)
        version.delete()
        if was_latest:
            next_version = DatasetVersion.objects.filter(dataset=dataset).order_by('-created_at').first()
            if next_version:
                next_version.is_latest = True
                next_version.save(update_fields=['is_latest'])
        messages.success(request, 'Versão apagada com sucesso.')

    return redirect('dataset_versions', dataset.id)


@login_required
def dataset_stats(request, id):
    from django.db.models import Count
    from django.utils import timezone
    from datetime import timedelta

    dataset = get_object_or_404(Dataset, id=id)

    if dataset.visibility == 'private' and dataset.owner != request.user and not request.user.is_staff:
        messages.error(request, 'Não tens permissão para ver este dataset.')
        return redirect('datasets')

    now               = timezone.now()
    total_downloads   = DownloadLog.objects.filter(dataset=dataset).count()
    downloads_7_days  = DownloadLog.objects.filter(dataset=dataset, downloaded_at__gte=now - timedelta(days=7)).count()
    downloads_30_days = DownloadLog.objects.filter(dataset=dataset, downloaded_at__gte=now - timedelta(days=30)).count()

    by_version = (
        DownloadLog.objects
        .filter(dataset=dataset, version__isnull=False)
        .values("version__version")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    recent_logs = (
        DownloadLog.objects
        .filter(dataset=dataset)
        .select_related("user", "version")
        .order_by("-downloaded_at")[:20]
    )

    return render(request, 'frontend/dataset_stats.html', {
        'dataset':           dataset,
        'total_downloads':   total_downloads,
        'downloads_7_days':  downloads_7_days,
        'downloads_30_days': downloads_30_days,
        'by_version':        by_version,
        'recent_logs':       recent_logs,
        'is_guest':          False,
    })


@login_required
def version_download(request, id, version_id):
    dataset = get_object_or_404(Dataset, id=id)
    version = get_object_or_404(DatasetVersion, id=version_id, dataset=dataset)

    if not version.file:
        messages.error(request, 'Ficheiro não encontrado.')
        return redirect('dataset_versions', dataset.id)

    try:
        file_obj = version.file.open('rb')
    except Exception:
        messages.error(request, 'Ficheiro não encontrado no armazenamento.')
        return redirect('dataset_versions', dataset.id)

    DownloadLog.objects.create(
        dataset=dataset,
        version=version,
        user=request.user,
        ip_address=request.META.get('REMOTE_ADDR'),
    )

    response = FileResponse(file_obj, as_attachment=True)
    response['Content-Length'] = version.file_size
    return response


@login_required
def auditoria(request):
    if not request.user.is_staff:
        messages.error(request, 'Não tens permissão para ver esta página.')
        return redirect('dashboard')

    logs     = AuditLog.objects.select_related("user").all()
    action   = request.GET.get('action', '')
    resource = request.GET.get('resource', '')
    user     = request.GET.get('user', '')

    if action:
        logs = logs.filter(action=action)
    if resource:
        logs = logs.filter(resource=resource)
    if user:
        logs = logs.filter(user__username__icontains=user)

    return render(request, 'frontend/auditoria.html', {'logs': logs})


@login_required
def dataset_submit(request, id):
    dataset = get_object_or_404(Dataset, id=id)
    if dataset.owner != request.user:
        messages.error(request, 'Não tens permissão.')
        return redirect('dataset_detail', dataset.id)
    if dataset.status != 'draft':
        messages.error(request, 'Só podes submeter datasets em rascunho.')
        return redirect('dataset_detail', dataset.id)
    if request.method == 'POST':
        dataset.status = 'pending'
        dataset.save()
        messages.success(request, 'Dataset submetido para aprovação.')
    return redirect('dataset_detail', dataset.id)


@login_required
def dataset_approve(request, id):
    if not request.user.is_staff:
        messages.error(request, 'Não tens permissão.')
        return redirect('dashboard')
    dataset = get_object_or_404(Dataset, id=id)
    if request.method == 'POST':
        dataset.status = 'published'
        dataset.save()
        logger.info(f'Dataset aprovado: "{dataset.name}" por {request.user.email}')
        messages.success(request, f'Dataset "{dataset.name}" aprovado e publicado.')
    return redirect('aprovacoes')


@login_required
def dataset_reject(request, id):
    if not request.user.is_staff:
        messages.error(request, 'Não tens permissão.')
        return redirect('dashboard')
    dataset = get_object_or_404(Dataset, id=id)
    if request.method == 'POST':
        motivo = request.POST.get('motivo', '')
        dataset.status = 'draft'
        dataset.save()
        logger.info(f'Dataset rejeitado: "{dataset.name}" por {request.user.email}. Motivo: {motivo}')
        messages.warning(request, f'Dataset "{dataset.name}" rejeitado.')
    return redirect('aprovacoes')


@login_required
def aprovacoes(request):
    if not request.user.is_staff:
        messages.error(request, 'Não tens permissão.')
        return redirect('dashboard')
    
    # Carrega os Datasets pendentes
    pendentes_qs = Dataset.objects.filter(status='pending').order_by('-created_at')
    
    # Carrega os Utilizadores pendentes (is_active=False)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    utilizadores_pendentes = User.objects.filter(is_active=False).order_by('-date_joined')
    
    # Enviamos várias chaves para garantir compatibilidade com o teu template HTML
    return render(request, 'frontend/aprovacoes.html', {
        'pendentes': pendentes_qs,
        'datasets_pendentes': pendentes_qs,  # <-- Muito provável que o teu HTML use isto
        'datasets': pendentes_qs,           # <-- Caso o teu loop use {% for d in datasets %}
        'utilizadores_pendentes': utilizadores_pendentes,
    })


@login_required
def user_approve_action(request, id):
    if not request.user.is_staff:
        messages.error(request, 'Não tens permissão.')
        return redirect('dashboard')
        
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user_to_approve = get_object_or_404(User, id=id)
    
    if request.method == 'POST':
        user_to_approve.is_active = True
        user_to_approve.save()
        
        audit(request, "update", "user", user_to_approve.id, f"Utilizador '{user_to_approve.username}' aprovado e ativado.")
        logger.info(f'Utilizador aprovado: {user_to_approve.email} por {request.user.email}')
        messages.success(request, f'Utilizador "{user_to_approve.username}" aprovado com sucesso!')
        
    return redirect('aprovacoes')


@login_required
def dataset_share(request, id):
    dataset = get_object_or_404(Dataset, id=id)

    # Verifica permissões
    if dataset.owner != request.user and not request.user.is_staff:
        messages.error(request, 'Não tens permissão para partilhar este dataset.')
        return redirect('dataset_detail', dataset.id)

    # O bloco POST começa aqui
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user_to_share = User.objects.get(email=email)
            
            if user_to_share == dataset.owner:
                messages.error(request, 'Não podes partilhar o dataset contigo próprio.')
            elif DatasetShare.objects.filter(dataset=dataset, shared_with=user_to_share).exists():
                messages.error(request, f'O dataset já está partilhado com {email}.')
            else:
                DatasetShare.objects.create(
                    dataset=dataset,
                    shared_with=user_to_share,
                    shared_by=request.user
                )
                messages.success(request, f'Dataset partilhado com {email}.')
                
        except User.DoesNotExist:
            messages.error(request, f'Não existe nenhum utilizador com o email {email}.')
            
    return redirect('dataset_detail', dataset.id)


@login_required
def dataset_share_remove(request, id, share_id):
    dataset = get_object_or_404(Dataset, id=id)

    if dataset.owner != request.user and not request.user.is_staff:
        messages.error(request, 'Não tens permissão.')
        return redirect('dataset_detail', dataset.id)

    if request.method == 'POST':
        share = get_object_or_404(DatasetShare, id=share_id, dataset=dataset)
        share.delete()
        messages.success(request, 'Partilha removida.')

    return redirect('dataset_share', dataset.id)


def landing(request):
    return render(request, 'frontend/landing.html')


def about(request):
    return render(request, 'frontend/about.html', {
        'is_guest': not request.user.is_authenticated,
    })

def home(request):
# Se o utilizador já estiver logado, vai direto para o dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    # Se NÃO estiver logado, renderiza a página Sobre (about) diretamente na raiz do site
    return render(request, 'frontend/about.html', {
        'is_guest': True,
    })