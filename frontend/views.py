from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from datasets.models import Dataset
from categories.models import Category

@login_required
def dashboard(request):
    recent_datasets = Dataset.objects.all().order_by('-created_at')[:5]
    total_datasets = Dataset.objects.count()
    total_categories = Category.objects.count()
    my_datasets = Dataset.objects.filter(owner=request.user).count()
    return render(request, 'frontend/dashboard.html', {
        'recent_datasets': recent_datasets,
        'total_datasets': total_datasets,
        'total_categories': total_categories,
        'my_datasets': my_datasets,
    })

@login_required
def datasets(request):
    datasets_list = Dataset.objects.all().order_by('-created_at')
    return render(request, 'frontend/datasets.html', {'datasets': datasets_list})

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'frontend/login.html', {'error': 'Email ou password incorretos'})
    return render(request, 'frontend/login.html')

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        from django.contrib.auth import get_user_model
        User = get_user_model()

        if User.objects.filter(username=username).exists():
            return render(request, 'frontend/register.html', {'error': 'Nome de utilizador já existe'})

        if User.objects.filter(email=email).exists():
            return render(request, 'frontend/register.html', {'error': 'Email já está registado'})

        user = User.objects.create_user(username=username, email=email, password=password)
        login(request, user)
        return redirect('dashboard')

    return render(request, 'frontend/register.html')

@login_required
def dataset_detail(request, id):
    dataset = get_object_or_404(Dataset, id=id)
    return render(request, 'frontend/dataset_detail.html', {'dataset': dataset})

@login_required
def dataset_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        category_id = request.POST.get('category')
        visibility = request.POST.get('visibility', 'public')
        status_val = request.POST.get('status', 'draft')

        category = None
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                pass

        dataset = Dataset.objects.create(
            name=name,
            description=description,
            category=category,
            owner=request.user,
            visibility=visibility,
            status=status_val
        )
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
    if request.method == 'POST':
        dataset.name = request.POST.get('name')
        dataset.description = request.POST.get('description')
        category_id = request.POST.get('category')
        dataset.visibility = request.POST.get('visibility', 'public')
        dataset.status = request.POST.get('status', 'draft')

        if category_id:
            try:
                dataset.category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                dataset.category = None
        else:
            dataset.category = None

        dataset.save()
        messages.success(request, 'Dataset atualizado com sucesso!')
        return redirect('dataset_detail', dataset.id)

    categories = Category.objects.all()
    return render(request, 'frontend/dataset_edit.html', {'dataset': dataset, 'categories': categories})

@login_required
def dataset_versions(request, id):
    from datasets.models import DatasetVersion
    dataset = get_object_or_404(Dataset, id=id)
    versions = DatasetVersion.objects.filter(dataset=dataset).order_by('-created_at')
    return render(request, 'frontend/dataset_versions.html', {
        'dataset': dataset,
        'versions': versions
    })

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dataset_delete(request, id):
    dataset = get_object_or_404(Dataset, id=id)
    if request.method == 'POST':
        dataset.delete()
    return redirect('datasets')

@login_required
def category_create(request):
    if not request.user.is_staff:
        messages.error(request, 'Não tens permissão para criar categorias.')
        return redirect('categories')

    if request.method == 'POST':
        name = request.POST.get('name')
        slug = request.POST.get('slug')
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
            Category.objects.create(
                name=name,
                slug=slug,
                description=description
            )
            messages.success(request, 'Categoria criada com sucesso!')
            return redirect('categories')

    return render(request, 'frontend/category_create.html')

@login_required
def version_create(request, id):
    from datasets.models import DatasetVersion
    dataset = get_object_or_404(Dataset, id=id)

    if request.method == 'POST':
        version = request.POST.get('version')
        title = request.POST.get('title')
        notes = request.POST.get('notes')
        file = request.FILES.get('file')

        if not version or not file:
            return render(request, 'frontend/version_create.html', {
                'dataset': dataset,
                'error': 'Versão e ficheiro são obrigatórios.'
            })

        if DatasetVersion.objects.filter(dataset=dataset, version=version).exists():
            return render(request, 'frontend/version_create.html', {
                'dataset': dataset,
                'error': f'Já existe a versão {version} neste dataset.'
            })

        # Marcar versão anterior como não latest
        DatasetVersion.objects.filter(dataset=dataset, is_latest=True).update(is_latest=False)

        DatasetVersion.objects.create(
            dataset=dataset,
            version=version,
            title=title,
            notes=notes,
            file=file,
            created_by=request.user,
            is_latest=True
        )

        messages.success(request, f'Versão {version} criada com sucesso!')
        return redirect('dataset_versions', dataset.id)

    return render(request, 'frontend/version_create.html', {'dataset': dataset})

@login_required
def profile(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'profile':
            request.user.username = request.POST.get('username')
            request.user.email = request.POST.get('email')
            request.user.first_name = request.POST.get('first_name')
            request.user.last_name = request.POST.get('last_name')
            request.user.save()
            messages.success(request, 'Perfil atualizado com sucesso!')

        elif form_type == 'password':
            current = request.POST.get('current_password')
            new = request.POST.get('new_password')
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