
from django.shortcuts import redirect, render
from blogs.models import Category , Blog
from assignments.models import About
from .forms import RegistrationForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import auth
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme

def home(request):
    featured_post = Blog.objects.select_related('author', 'Category').filter(
        is_featured=True, status='Published'
    ).order_by('-updated_at')
    posts = Blog.objects.select_related('author', 'Category').filter(
        is_featured=False, status='Published'
    )
    
    # fetch about us
    try:
        about = About.objects.get()
    except:
        about = None

    context = {
        'featured_post' : featured_post,
        'posts':posts,
        'about': about,
    }

    return render(request, "home.html", context)

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created. You can now log in and comment.')
            return redirect('login')
        
    else:
        form = RegistrationForm()
    context = {
        'form' : form,
    }
    return render(request, 'register.html', context)

def login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = auth.authenticate(username=username, password=password)
            if user is not None:
                auth.login(request,user)
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url and url_has_allowed_host_and_scheme(
                    next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
                ):
                    return redirect(next_url)
                if user.is_superuser or user.groups.filter(name__in=('Manager', 'Editor')).exists():
                    return redirect('dashboard')
                return redirect('home')
    else:
        form = AuthenticationForm()
    context = {
        'form': form,
    }
    return render(request, 'login.html', context)

def logout(request):
    auth.logout(request)
    
    return redirect('home')
