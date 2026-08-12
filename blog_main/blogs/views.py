from django.http import HttpResponse
from django.shortcuts import render ,get_object_or_404, redirect

from blogs.models import Blog , Category
from django.db.models import Q



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
    context = {
        'single_blog': single_blog,
    }
    return render(request , 'blogs.html' , context)

def search(request):
    keyword = request.GET.get('keyword')

    blogs = Blog.objects.filter(Q(title__icontains=keyword) | Q(short_description__icontains=keyword) | Q(blog_body__icontains=keyword), status = 'Published')
    
    context = {
        'blogs': blogs,
        'keyword': keyword,
    }
    return render(request, 'search.html', context)

# Create your views here.
