from django.contrib import messages
from django.db.models import F, Q
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from blogs.models import Blog, Category
from .forms import CommentForm



def posts_by_category(request, category_id):
    #print(category_id)
    # Fetch the posts that belong to the category with the category_id
    posts = Blog.objects.filter(
        status = 'Published' , 
        Category = category_id
    )
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
        'category_name': category.category_name,
    }
    return render(request, 'posts_by_category.html', context)

def blogs(request, slug):
    single_blog = get_object_or_404(Blog, slug = slug, status = 'Published')

    viewed_posts = request.session.get('viewed_posts', [])
    if single_blog.pk not in viewed_posts:
        Blog.objects.filter(pk=single_blog.pk).update(views=F('views') + 1)
        viewed_posts.append(single_blog.pk)
        request.session['viewed_posts'] = viewed_posts[-100:]
        single_blog.refresh_from_db(fields=['views'])

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to write a comment.')
            return redirect(f"{reverse('login')}?next={request.path}")
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.blog = single_blog
            comment.user = request.user
            comment.save()
            messages.success(request, 'Your comment was added.')
            return redirect(f"{request.path}#comments")
    else:
        comment_form = CommentForm()

    comments = single_blog.comments.filter(is_approved=True).select_related('user')
    related_posts = Blog.objects.filter(
        Category=single_blog.Category, status='Published'
    ).exclude(pk=single_blog.pk)[:3]
    context = {
        'single_blog': single_blog,
        'comments': comments,
        'comment_count': comments.count(),
        'comment_form': comment_form,
        'related_posts': related_posts,
    }
    return render(request , 'blogs.html' , context)

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
