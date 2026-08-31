from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from blogs.models import Blog, Category, Comment
from dashboards.forms import AddUserForm, BlogPostForm, CategoryForm, EditUserForm


def is_manager(user):
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name='Manager').exists()
    )


def is_editor(user):
    return user.is_authenticated and user.groups.filter(name='Editor').exists()


def dashboard_user_required(view_func):
    @login_required(login_url='login')
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not (is_manager(request.user) or is_editor(request.user)):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapped


def manager_required(view_func):
    @login_required(login_url='login')
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not is_manager(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapped


def visible_posts_for(user):
    posts = Blog.objects.select_related('Category', 'author')
    return posts if is_manager(user) else posts.filter(author=user)


@dashboard_user_required
def dashboards(request):
    visible_posts = visible_posts_for(request.user)
    context = {
        'category_count': Category.objects.count(),
        'blogs_count': visible_posts.count(),
        'published_count': visible_posts.filter(status='Published').count(),
        'draft_count': visible_posts.filter(status='Draft').count(),
        'total_views': visible_posts.aggregate(total=Sum('views'))['total'] or 0,
        'comment_count': Comment.objects.filter(blog__in=visible_posts).count(),
        'user_count': User.objects.count() if is_manager(request.user) else None,
        'recent_posts': visible_posts[:5],
    }
    return render(request, 'dashboard/dashboard.html', context)


@manager_required
def categories(request):
    return render(request, 'dashboard/categories.html', {
        'categories': Category.objects.all().order_by('category_name'),
    })


@manager_required
def add_category(request):
    form = CategoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Category added successfully.')
        return redirect('categories')
    return render(request, 'dashboard/add_category.html', {'form': form})


@manager_required
def edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, instance=category)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Category updated successfully.')
        return redirect('categories')
    return render(request, 'dashboard/edit_category.html', {
        'form': form,
        'category': category,
    })


@manager_required
@require_POST
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.delete()
    messages.success(request, 'Category deleted successfully.')
    return redirect('categories')


@dashboard_user_required
def posts(request):
    return render(request, 'dashboard/posts.html', {
        'posts': visible_posts_for(request.user),
    })


@dashboard_user_required
def add_post(request):
    form = BlogPostForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        messages.success(request, 'Post added successfully.')
        return redirect('posts')
    return render(request, 'dashboard/add_post.html', {'form': form})


@dashboard_user_required
def edit_post(request, pk):
    post = get_object_or_404(visible_posts_for(request.user), pk=pk)
    form = BlogPostForm(request.POST or None, request.FILES or None, instance=post)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Post updated successfully.')
        return redirect('posts')
    return render(request, 'dashboard/edit_post.html', {'form': form, 'post': post})


@dashboard_user_required
@require_POST
def delete_post(request, pk):
    post = get_object_or_404(visible_posts_for(request.user), pk=pk)
    post.delete()
    messages.success(request, 'Post deleted successfully.')
    return redirect('posts')


@manager_required
def users(request):
    users_list = User.objects.prefetch_related('groups').order_by('username')
    return render(request, 'dashboard/users.html', {'users_list': users_list})


@manager_required
def add_user(request):
    form = AddUserForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'User added successfully.')
        return redirect('users')
    return render(request, 'dashboard/add_user.html', {'form': form})


@manager_required
def edit_user(request, pk):
    edited_user = get_object_or_404(User, pk=pk)
    if edited_user.is_superuser and not request.user.is_superuser:
        raise PermissionDenied
    form = EditUserForm(request.POST or None, instance=edited_user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'User updated successfully.')
        return redirect('users')
    return render(request, 'dashboard/edit_user.html', {
        'form': form,
        'edited_user': edited_user,
    })


@manager_required
@require_POST
def delete_user(request, pk):
    deleted_user = get_object_or_404(User, pk=pk)
    if deleted_user == request.user:
        messages.error(request, 'You cannot delete your own account while signed in.')
    elif deleted_user.is_superuser:
        messages.error(request, 'A superuser cannot be deleted from this dashboard.')
    else:
        deleted_user.delete()
        messages.success(request, 'User deleted successfully.')
    return redirect('users')
