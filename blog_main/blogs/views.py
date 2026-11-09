from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F, Q
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from blogs.models import Blog, Category, SavedPost
from blogs.context_processors import absolute_public_url
from blogs.seo import serialize_json_ld
from .forms import CommentForm



def posts_by_category(request, category_id):
    #print(category_id)
    # Fetch the posts that belong to the category with the category_id
    posts = Blog.objects.filter(
        status = 'Published' , 
        Category = category_id
    ).prefetch_related('author', 'Category')
    #USE TRY AND EXECPT WHEN YOU WANT TO DO SOME CUSTOM ACTION WHEN THE CATEGORY DOESNOT EXIST
    # try:
    #     category = Category.objects.get(pk=category_id)
    # except:
    #     #redirect to home page without showing the error
    #     return redirect('home')

    #Use get_object_or_404 when you want to show 404 error PAGE IF THE CATEGORY DOESNOT THERE
    category = get_object_or_404(Category, pk=category_id)

    
    context = {
        'posts': posts,
        'category': category,
        'category_name': category.category_name,
        'saved_blog_ids': _saved_blog_ids(request),
    }
    return render(request, 'posts_by_category.html', context)

def blogs(request, slug):
    single_blog = get_object_or_404(
        Blog.objects.prefetch_related('author', 'Category'),
        slug=slug,
        status='Published'
    )

    # MongoDB ObjectId must be converted to string before
    # storing it in the Django session.
    blog_id = str(single_blog.pk)

    viewed_posts = request.session.get('viewed_posts', [])

    if blog_id not in viewed_posts:
        Blog.objects.filter(pk=single_blog.pk).update(
            views=F('views') + 1
        )

        viewed_posts.append(blog_id)

        request.session['viewed_posts'] = viewed_posts[-100:]

        single_blog.refresh_from_db(fields=['views'])

    # -----------------------------------------------------
    # COMMENTS
    # -----------------------------------------------------

    if request.method == 'POST':

        if not request.user.is_authenticated:
            messages.warning(
                request,
                'Please log in to write a comment.'
            )

            return redirect(
                f"{reverse('login')}?next={request.path}"
            )

        comment_form = CommentForm(request.POST)

        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.blog = single_blog
            comment.user = request.user
            comment.save()

            messages.success(
                request,
                'Your comment was added.'
            )

            return redirect(
                f"{request.path}#comments"
            )

    else:
        comment_form = CommentForm()

    # Do not use select_related() with MongoDB backend.
    comments = single_blog.comments.filter(
        is_approved=True
    )

    related_posts = Blog.objects.filter(
        Category=single_blog.Category,
        status='Published'
    ).exclude(
        pk=single_blog.pk
    ).prefetch_related('author', 'Category')[:3]

    # Do not use select_related() here either.
    popular_posts = Blog.objects.filter(
        status='Published'
    ).exclude(
        pk=single_blog.pk
    ).prefetch_related(
        'author',
        'Category',
    ).order_by(
        '-views',
        '-created_at'
    )[:4]

    canonical_url = absolute_public_url(reverse('blogs', args=[single_blog.slug]))
    category_url = absolute_public_url(
        reverse('posts_by_category', args=[str(single_blog.Category.pk)])
    )
    image_url = (
        absolute_public_url(single_blog.featured_image.url)
        if single_blog.featured_image
        else ''
    )
    blog_posting = {
        '@context': 'https://schema.org',
        '@type': 'BlogPosting',
        'headline': single_blog.seo_title_value,
        'description': single_blog.meta_description_value,
        'datePublished': single_blog.created_at.isoformat(),
        'dateModified': single_blog.updated_at.isoformat(),
        'author': {
            '@type': 'Person',
            'name': single_blog.author_name,
        },
        'publisher': {
            '@type': 'Organization',
            'name': 'ZaraTech',
            'url': absolute_public_url('/'),
        },
        'mainEntityOfPage': {
            '@type': 'WebPage',
            '@id': canonical_url,
        },
    }
    if image_url:
        blog_posting['image'] = [image_url]

    breadcrumb_list = {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        'itemListElement': [
            {
                '@type': 'ListItem',
                'position': 1,
                'name': 'Home',
                'item': absolute_public_url('/'),
            },
            {
                '@type': 'ListItem',
                'position': 2,
                'name': single_blog.Category.category_name,
                'item': category_url,
            },
            {
                '@type': 'ListItem',
                'position': 3,
                'name': single_blog.title,
                'item': canonical_url,
            },
        ],
    }

    context = {
        'single_blog': single_blog,
        'article_canonical_url': canonical_url,
        'social_image_url': image_url,
        'blog_posting_json': serialize_json_ld(blog_posting),
        'breadcrumb_json': serialize_json_ld(breadcrumb_list),
        'comments': comments,
        'comment_count': comments.count(),
        'comment_form': comment_form,
        'related_posts': related_posts,
        'popular_posts': popular_posts,
        'saved_blog_ids': _saved_blog_ids(request),
    }

    return render(
        request,
        'blogs.html',
        context
    )


def _saved_blog_ids(request):
    if not request.user.is_authenticated:
        return set()

    return set(
        SavedPost.objects.filter(
            user=request.user,
        ).values_list('blog_id', flat=True)
    )


def _bookmark_return_url(request, fallback):
    next_url = request.POST.get('next', '')

    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url

    return fallback


@login_required(login_url='login')
@require_POST
def save_blog(request, slug):
    blog = get_object_or_404(
        Blog,
        slug=slug,
        status='Published',
    )
    SavedPost.objects.get_or_create(
        user=request.user,
        blog=blog,
    )
    messages.success(request, 'Article saved.')
    return redirect(
        _bookmark_return_url(
            request,
            reverse('blogs', args=[blog.slug]),
        )
    )


@login_required(login_url='login')
@require_POST
def unsave_blog(request, slug):
    blog = get_object_or_404(
        Blog,
        slug=slug,
        status='Published',
    )
    SavedPost.objects.filter(
        user=request.user,
        blog=blog,
    ).delete()
    messages.success(request, 'Article removed from saved articles.')
    return redirect(
        _bookmark_return_url(
            request,
            reverse('blogs', args=[blog.slug]),
        )
    )


@login_required(login_url='login')
def saved_posts(request):
    saved_items = list(
        SavedPost.objects.filter(user=request.user)
    )
    blog_ids = [item.blog_id for item in saved_items]
    blogs_by_id = {
        blog.pk: blog
        for blog in Blog.objects.filter(
            pk__in=blog_ids,
            status='Published',
        ).prefetch_related('author', 'Category')
    }
    posts = [
        blogs_by_id[item.blog_id]
        for item in saved_items
        if item.blog_id in blogs_by_id
    ]

    return render(
        request,
        'saved_posts.html',
        {
            'posts': posts,
            'saved_blog_ids': set(blog_ids),
        },
    )

def search(request):
    keyword = request.GET.get('keyword', '').strip()

    blogs = Blog.objects.none()
    if keyword:
        blogs = Blog.objects.filter(
            Q(title__icontains=keyword)
            | Q(short_description__icontains=keyword)
            | Q(blog_body__icontains=keyword),
            status='Published',
        )
    
    context = {
        'blogs': blogs,
        'keyword': keyword,
    }
    return render(request, 'search.html', context)

# Create your views here.
