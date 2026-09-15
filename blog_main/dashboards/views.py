from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from assignments.models import About, SocialLink
from blogs.models import Blog, Category, Comment
from dashboards.forms import (
    AboutForm,
    AddUserForm,
    BlogPostForm,
    CategoryForm,
    EditUserForm,
    SocialLinkForm,
)


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
        'user_count': User.objects.filter(is_active=True).count() if is_manager(request.user) else None,
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
    users_list = User.objects.filter(is_active=True).order_by('username')

    return render(
        request,
        'dashboard/users.html',
        {'users_list': users_list}
    )


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


@dashboard_user_required
def dashboard_about(request):
    about_records = About.objects.order_by('-updated_at', '-created_at', '-pk')
    about = about_records.first()
    form = AboutForm(request.POST or None, instance=about)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'About section updated successfully.')
        return redirect('dashboard_about')

    return render(request, 'dashboard/about.html', {
        'form': form,
        'about': about,
        'multiple_about_records': about_records.count() > 1,
    })


@dashboard_user_required
def dashboard_social_links(request):
    return render(request, 'dashboard/social_links.html', {
        'social_links_list': SocialLink.objects.all().order_by('platform'),
    })


@dashboard_user_required
def dashboard_add_social_link(request):
    form = SocialLinkForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Social link added successfully.')
        return redirect('dashboard_social_links')

    return render(request, 'dashboard/social_link_form.html', {
        'form': form,
        'page_title': 'Add Social Link',
        'submit_label': 'Add Social Link',
    })


@dashboard_user_required
def dashboard_edit_social_link(request, pk):
    social_link = get_object_or_404(SocialLink, pk=pk)
    form = SocialLinkForm(request.POST or None, instance=social_link)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Social link updated successfully.')
        return redirect('dashboard_social_links')

    return render(request, 'dashboard/social_link_form.html', {
        'form': form,
        'page_title': 'Edit Social Link',
        'submit_label': 'Save Changes',
        'social_link': social_link,
    })


@dashboard_user_required
def dashboard_delete_social_link(request, pk):
    social_link = get_object_or_404(SocialLink, pk=pk)
    if request.method == 'POST':
        platform = social_link.platform
        social_link.delete()
        messages.success(request, f'{platform} social link deleted successfully.')
        return redirect('dashboard_social_links')

    return render(request, 'dashboard/social_link_delete.html', {
        'social_link': social_link,
    })


@dashboard_user_required
def dashboard_comments(request):
    status_filter = request.GET.get('status', 'all')
    comments = Comment.objects.all().order_by('-created_at')

    if status_filter == 'approved':
        comments = comments.filter(is_approved=True)
    elif status_filter == 'unapproved':
        comments = comments.filter(is_approved=False)
    else:
        status_filter = 'all'

    paginator = Paginator(comments, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/comments.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
    })


@dashboard_user_required
def dashboard_comment_detail(request, pk):
    return render(request, 'dashboard/comment_detail.html', {
        'comment': get_object_or_404(Comment, pk=pk),
    })


@dashboard_user_required
@require_POST
def dashboard_comment_approve(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if not comment.is_approved:
        comment.is_approved = True
        comment.save()
    messages.success(request, 'Comment approved successfully.')
    return redirect('dashboard_comments')


@dashboard_user_required
@require_POST
def dashboard_comment_unapprove(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if comment.is_approved:
        comment.is_approved = False
        comment.save()
    messages.success(request, 'Comment unapproved successfully.')
    return redirect('dashboard_comments')


@manager_required
def dashboard_comment_delete(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if request.method == 'POST':
        comment.delete()
        messages.success(request, 'Comment deleted successfully.')
        return redirect('dashboard_comments')

    return render(request, 'dashboard/comment_delete.html', {
        'comment': comment,
    })
