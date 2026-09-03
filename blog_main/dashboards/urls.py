from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('', views.dashboards, name='dashboard'),

    path(
        'admin/',
        RedirectView.as_view(pattern_name='admin:index', permanent=False),
        name='dashboard_admin',
    ),

    # Category CRUD
    path('categories/', views.categories, name='categories'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/edit/<str:pk>/', views.edit_category, name='edit_category'),
    path('categories/delete/<str:pk>/', views.delete_category, name='delete_category'),

    # Blog post CRUD
    path('posts/', views.posts, name='posts'),
    path('posts/add/', views.add_post, name='add_post'),
    path('posts/edit/<str:pk>/', views.edit_post, name='edit_post'),
    path('posts/delete/<str:pk>/', views.delete_post, name='delete_post'),

    # User management
    path('users/', views.users, name='users'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/edit/<str:pk>/', views.edit_user, name='edit_user'),
    path('users/delete/<str:pk>/', views.delete_user, name='delete_user'),
]
