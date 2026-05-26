import logging

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Q
from datasets.models import Dataset, DatasetVersion, Comment
from categories.models import Category

logger = logging.getLogger('accounts')


@login_required
def dashboard(request):
    if request.user.is_staff:
        recent_datasets = Dataset.objects.all().order_by('-created_at')[:5]
        total_datasets = Dataset.objects.count()
        total_versions = DatasetVersion.objects.count()
    else:
        qs = Dataset.objects.filter(
            Q(visibility='public') | Q(owner=request.user)
        )
        recent_datasets = qs.order_by('-created_at')[:5]
        total_datasets = qs.count()
        total_versions = DatasetVersion.objects.filter(dataset__in=qs).count()

    total_categories = Category.objects.count()
    my_datasets = Dataset.objects.filter(owner=request.user).count()
    return render(request, 'frontend/dashboard.html', {
        'recent_datasets': recent_datasets,
        'total_datasets': total_datasets,
        'total_categories': total_categories,
        'total_versions': total_versions,
        'my_datasets': my_datasets,
    })


@login_required
def datasets(request):
    search            = request.GET.get('search', '').strip()
    category_filter   = request.GET.get('category', '')
    visibility_filter = request.GET.get('visibility', '')
    status_filter     = request.GET.get('status', '')

    if request.user.is_staff:
        qs = Dataset.objects.all()
    else:
        qs = Dataset.objects.filter(
            Q(visibility='public') | Q(owner=request.user)
        )

    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
    if category_filter:
        qs = qs.filter(category__slug=category_filter)
    if visibility_filter:
        qs = qs.filter(visibility=visibility_filter)
    if status_filter:
        qs = qs.filter(status=status_filter)

    qs = qs.order_by('-created_at')
    categories = Category.objects.all()
    return render(request, 'frontend/datasets.html', {
        'datasets': qs,
        'categories': categories,
        'search': search,
        'category_filter': category_filter,
        'visibility_filter': visibility_filter,
        'status_filter': status_filter,
    })


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
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
def dataset_detail(request, id):
    dataset = get_object_or_404(Dataset, id=id)

    if dataset.visibility == 'private' and dataset.owner != request.user and not request.user.is_staff:
        messages.error(request, 'Não tens permissão para ver este dataset.')
        return redirect('datasets')

    versions = DatasetVersion.objects.filter(dataset=dataset).order_by('-created_at')
    comments = Comment.objects.filter(dataset=dataset).order_by('created_at')
    is_owner = dataset.owner == request.user

    tags = []
    if hasattr(dataset, 'metadata') and dataset.metadata:
        tags = dataset.metadata.tags or []

    return render(request, 'frontend/dataset_detail.html', {
        'dataset': dataset,
        'versions': versions,
        'comments': comments,
        'is_owner': is_owner,
        'tags': tags,
    })


@login_required
def dataset_create(request):
    if request.method == 'POST':
        name        = request.POST.get('name')
        description = request.POST.get('description')
        category_id = request.POST.get('category')
        visibility  = request.POST.get('visibility', 'public')
        status_val  = request.POST.get('status', 'draft')
        tags_raw    = request.POST.get('tags', '')
        tags        = [t.strip() for t in tags_raw.split(',') if t.strip()]

        category = None
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                pass

        from datasets.models import DatasetMetadata
        dataset = Dataset.objects.create(
            name=name, description=description, category=category,
            owner=request.user, visibility=visibility, status=status_val
        )
        DatasetMetadata.objects.create(dataset=dataset, tags=tags)

        logger.info(f'Dataset criado: "{dataset.name}" por {request.user.email}')
        messages.success(request, 'Dataset criado com sucesso!')
        return redirect('dataset_detail', dataset.id)

    categories = Category.objects.all()
    return render(request, 'frontend/dataset_create.html', {'categories': categories})


@login_required
def categories(request):
    all_categories = Category.objects.all()
    return render(request, 'frontend/categories.html', {'categories': all_categories})


@login_required
def dataset_edit(request, id):
    dataset = get_object_or_404(Dataset, id=id)

    if dataset.owner != request.user and not request.user.is_staff:
        messages.error(request, 'Não tens permissão para editar este dataset.')
        return redirect('dataset_detail', dataset.id)

    if request.method == 'POST':
        dataset.name        = request.POST.get('name')
        dataset.description = request.POST.get('description')
        category_id         = request.POST.get('category')
        dataset.visibility  = request.POST.get('visibility', 'public')
        dataset.status      = request.POST.get('status', 'draft')
        tags_raw            = request.POST.get('tags', '')
        tags                = [t.strip() for t in tags_raw.split(',') if t.strip()]

        if category_id:
            try:
                dataset.category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                dataset.category = None
        else:
            dataset.category = None

        dataset.save()

        from datasets.models import DatasetMetadata
        metadata, _ = DatasetMetadata.objects.get_or_create(dataset=dataset)
        metadata.tags = tags
        metadata.save()

        logger.info(f'Dataset editado: "{dataset.name}" por {request.user.email}')
        messages.success(request, 'Dataset atualizado com sucesso!')
        return redirect('dataset_detail', dataset.id)

    tags_str = ''
    if hasattr(dataset, 'metadata') and dataset.metadata:
        tags_str = ', '.join(dataset.metadata.tags or [])

    categories = Category.objects.all()
    return render(request, 'frontend/dataset_edit.html', {
        'dataset': dataset,
        'categories': categories,
        'tags_str': tags_str,
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
        'dataset': dataset,
        'versions': versions,
        'is_owner': is_owner,
    })


def logout_view(request):
    logger.info(f'Logout: {request.user.email if request.user.is_authenticated else "anónimo"}')
    logout(request)
    return redirect('login')


@login_required
def dataset_delete(request, id):
    dataset = get_object_or_404(Dataset, id=id)

    if dataset.owner != request.user and not request.user.is_staff:
        messages.error(request, 'Não tens permissão para apagar este dataset.')
        return redirect('dataset_detail', dataset.id)

    if request.method == 'POST':
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
            Category.objects.create(name=name, slug=slug, description=description)
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

        DatasetVersion.objects.filter(dataset=dataset, is_latest=True).update(is_latest=False)
        DatasetVersion.objects.create(
            dataset=dataset, version=version, title=title,
            notes=notes, file=file, created_by=request.user, is_latest=True
        )
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
    User = get_user_model()
    all_users = User.objects.all().order_by('date_joined')
    return render(request, 'frontend/users.html', {'users': all_users})


@login_required
def user_edit(request, id):
    if not request.user.is_staff:
        messages.error(request, 'Não tens permissão para editar utilizadores.')
        return redirect('dashboard')
    from django.contrib.auth import get_user_model
    User = get_user_model()
    edited_user = get_object_or_404(User, id=id)
    if request.method == 'POST':
        edited_user.username   = request.POST.get('username')
        edited_user.email      = request.POST.get('email')
        edited_user.first_name = request.POST.get('first_name')
        edited_user.last_name  = request.POST.get('last_name')
        edited_user.is_staff   = request.POST.get('is_staff') == 'on'
        edited_user.is_active  = request.POST.get('is_active') == 'on'
        edited_user.save()
        logger.info(f'Utilizador editado: {edited_user.email} por {request.user.email}')
        messages.success(request, 'Utilizador atualizado com sucesso!')
        return redirect('users')
    return render(request, 'frontend/user_edit.html', {'edited_user': edited_user})


@login_required
def user_delete(request, id):
    if not request.user.is_staff:
        return redirect('dashboard')
    from django.contrib.auth import get_user_model
    User = get_user_model()
    edited_user = get_object_or_404(User, id=id)
    if request.method == 'POST':
        logger.info(f'Utilizador apagado: {edited_user.email} por {request.user.email}')
        edited_user.delete()
        messages.success(request, 'Utilizador apagado com sucesso.')
    return redirect('users')


@login_required
def version_delete(request, id, version_id):
    import os
    dataset = get_object_or_404(Dataset, id=id)
    version = get_object_or_404(DatasetVersion, id=version_id, dataset=dataset)

    if dataset.owner != request.user and not request.user.is_staff:
        messages.error(request, 'Não tens permissão para apagar esta versão.')
        return redirect('dataset_versions', dataset.id)

    if request.method == 'POST':
        was_latest = version.is_latest
        if version.file and os.path.exists(version.file.path):
            os.remove(version.file.path)
        logger.info(f'Versão apagada: "{dataset.name}" v{version.version} por {request.user.email}')
        version.delete()
        if was_latest:
            next_version = DatasetVersion.objects.filter(dataset=dataset).order_by('-created_at').first()
            if next_version:
                next_version.is_latest = True
                next_version.save(update_fields=['is_latest'])
        messages.success(request, 'Versão apagada com sucesso.')

    return redirect('dataset_versions', dataset.id)


@login_required
def comment_create(request, id):
    dataset = get_object_or_404(Dataset, id=id)
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            Comment.objects.create(
                dataset=dataset,
                author=request.user,
                content=content
            )
    return redirect('dataset_detail', dataset.id)


@login_required
def comment_delete(request, id, comment_id):
    dataset = get_object_or_404(Dataset, id=id)
    comment = get_object_or_404(Comment, id=comment_id, dataset=dataset)
    if request.user == comment.author or request.user.is_staff:
        if request.method == 'POST':
            comment.delete()
    return redirect('dataset_detail', dataset.id)