import csv
import io
import logging

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Q
from django.http import FileResponse, JsonResponse
from categories.models import Category
from datasets.models import Dataset, DatasetVersion, DownloadLog, AuditLog, DatasetFavorite, DatasetShare
from datasets.audit import audit, audit_dataset_changes

logger = logging.getLogger('accounts')


def dashboard(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            recent_datasets = Dataset.objects.all().order_by('-created_at')[:5]
            total_datasets  = Dataset.objects.count()
            total_versions  = DatasetVersion.objects.count()
        else:
            qs = Dataset.objects.filter(
                Q(visibility='public') | Q(owner=request.user)
            )
            recent_datasets = qs.order_by('-created_at')[:5]
            total_datasets  = qs.count()
            total_versions  = DatasetVersion.objects.filter(dataset__in=qs).count()
        my_datasets = Dataset.objects.filter(owner=request.user).count()
    else:
        # Guest view: only public datasets
        recent_datasets = Dataset.objects.filter(visibility='public').order_by('-created_at')[:5]
        total_datasets  = Dataset.objects.filter(visibility='public').count()
        total_versions  = DatasetVersion.objects.filter(dataset__in=Dataset.objects.filter(visibility='public')).count()
        my_datasets     = 0

    total_categories = Category.objects.count()
    return render(request, 'frontend/dashboard.html', {
        'recent_datasets': recent_datasets,
        'total_datasets':  total_datasets,
        'total_categories': total_categories,
        'total_versions':  total_versions,
        'my_datasets':     my_datasets,
        'is_guest':        not request.user.is_authenticated,
    })



def datasets(request):
    search            = request.GET.get('search', '').strip()
    category_filter   = request.GET.get('category', '')
    visibility_filter = request.GET.get('visibility', '')
    status_filter     = request.GET.get('status', '')
    favorites_filter  = request.GET.get('favorites', '')

    if request.user.is_authenticated:
        if request.user.is_staff:
            qs = Dataset.objects.all()
        else:
            qs = Dataset.objects.filter(
                Q(visibility='public') | Q(owner=request.user)
            )
    else:
        # Guest view: only public datasets
        qs = Dataset.objects.filter(visibility='public')

    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
    if category_filter:
        qs = qs.filter(category__slug=category_filter)
    if visibility_filter and request.user.is_authenticated:
        qs = qs.filter(visibility=visibility_filter)
    if status_filter and request.user.is_authenticated:
        qs = qs.filter(status=status_filter)
    if favorites_filter and request.user.is_authenticated:
        favorited_ids = DatasetFavorite.objects.filter(
            user=request.user
        ).values_list('dataset_id', flat=True)
        qs = qs.filter(id__in=favorited_ids)

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
        'is_guest':          not request.user.is_authenticated,
    })


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
            return render(request, 'frontend/login.html', {'error': 'Email ou password incorretos'})
    return render(request, 'frontend/login.html')


@login_required
def register_view(request):
    if not request.user.is_staff:
        messages.error(request, 'Apenas administradores podem registar novos utilizadores.')
        return redirect('dashboard')

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

        User.objects.create_user(username=username, email=email, password=password)
        logger.info(f'Utilizador criado: {email} por {request.user.email}')
        messages.success(request, 'Utilizador criado com sucesso!')
        return redirect('users')

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
    dataset   = get_object_or_404(Dataset, id=id)
    has_share = False
    if request.user.is_authenticated:
        has_share = DatasetShare.objects.filter(dataset=dataset, shared_with=request.user).exists()

    if dataset.visibility == 'private' and request.user.is_authenticated and dataset.owner != request.user and not request.user.is_staff and not has_share:
        messages.error(request, 'Não tens permissão para ver este dataset.')
        return redirect('datasets')
    elif dataset.visibility == 'private' and not request.user.is_authenticated:
        messages.error(request, 'Não tens permissão para ver este dataset.')
        return redirect('datasets')

    versions     = DatasetVersion.objects.filter(dataset=dataset).order_by('-created_at')
    is_owner     = request.user.is_authenticated and dataset.owner == request.user
    is_favorited = request.user.is_authenticated and DatasetFavorite.objects.filter(user=request.user, dataset=dataset).exists()

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
        'is_guest':     not request.user.is_authenticated,
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
        messages.success(request, 'Dataset atualizado com sucesso!')
        return redirect('dataset_detail', dataset.id)

    categories = Category.objects.all()
    return render(request, 'frontend/dataset_edit.html', {'dataset': dataset, 'categories': categories})


def dataset_versions(request, id):
    dataset = get_object_or_404(Dataset, id=id)

    if dataset.visibility == 'private' and not request.user.is_authenticated:
        messages.error(request, 'Não tens permissão para ver este dataset.')
        return redirect('datasets')
    elif dataset.visibility == 'private' and request.user.is_authenticated and dataset.owner != request.user and not request.user.is_staff:
        messages.error(request, 'Não tens permissão para ver este dataset.')
        return redirect('datasets')

    versions = DatasetVersion.objects.filter(dataset=dataset).order_by('-created_at')
    is_owner = request.user.is_authenticated and dataset.owner == request.user
    return render(request, 'frontend/dataset_versions.html', {
        'dataset':  dataset,
        'versions': versions,
        'is_owner': is_owner,
    })


def logout_view(request):
    logger.info(f'Logout: {request.user.email if request.user.is_authenticated else "anonimo"}')
    logout(request)
    return redirect('login')


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
        form_type = request.POST.get('form_type')

        if form_type == 'profile':
            request.user.username   = request.POST.get('username')
            request.user.email      = request.POST.get('email')
            request.user.first_name = request.POST.get('first_name')
            request.user.last_name  = request.POST.get('last_name')
            request.user.save()
            messages.success(request, 'Perfil atualizado com sucesso!')

        elif form_type == 'password':
            current = request.POST.get('current_password')
            new     = request.POST.get('new_password')
            confirm = request.POST.get('confirm_password')

            if not request.user.check_password(current):
                messages.error(request, 'Password atual incorreta.')
            elif new != confirm:
                messages.error(request, 'As passwords não coincidem.')
            elif len(new) < 6:
                messages.error(request, 'A nova password deve ter pelo menos 6 caracteres.')
            else:
                request.user.set_password(new)
                request.user.save()
                login(request, request.user)
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


def dataset_stats(request, id):
    from django.db.models import Count
    from django.utils import timezone
    from datetime import timedelta

    dataset = get_object_or_404(Dataset, id=id)

    if dataset.visibility == 'private' and request.user.is_authenticated and dataset.owner != request.user and not request.user.is_staff:
        messages.error(request, 'Não tens permissão para ver este dataset.')
        return redirect('datasets')
    elif dataset.visibility == 'private' and not request.user.is_authenticated:
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
        'is_guest':          not request.user.is_authenticated,
    })


def version_download(request, id, version_id):
    dataset = get_object_or_404(Dataset, id=id)
    version = get_object_or_404(DatasetVersion, id=version_id, dataset=dataset)

    # Permitir apenas downloads de datasets públicos para guests
    if not request.user.is_authenticated and dataset.visibility != 'public':
        messages.error(request, 'Não tens permissão para fazer download deste ficheiro.')
        return redirect('dataset_detail', dataset.id)

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
        user=request.user if request.user.is_authenticated else None,
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
    pendentes = Dataset.objects.filter(status='pending').order_by('-created_at')
    return render(request, 'frontend/aprovacoes.html', {'pendentes': pendentes})


@login_required
def dataset_share(request, id):
    dataset = get_object_or_404(Dataset, id=id)

    if dataset.owner != request.user and not request.user.is_staff:
        messages.error(request, 'Não tens permissão para partilhar este dataset.')
        return redirect('dataset_detail', dataset.id)

    from django.contrib.auth import get_user_model
    User = get_user_model()

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
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

    shares = DatasetShare.objects.filter(dataset=dataset).select_related('shared_with')
    return render(request, 'frontend/dataset_share.html', {
        'dataset': dataset,
        'shares':  shares,
    })


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
    """About page accessible to all users (authenticated and guests)."""
    return render(request, 'frontend/about.html', {
        'is_guest': not request.user.is_authenticated,
    })
