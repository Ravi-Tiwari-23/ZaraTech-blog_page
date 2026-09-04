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

    # About section
    path('about/', views.dashboard_about, name='dashboard_about'),

    # Social link CRUD
    path('social-links/', views.dashboard_social_links, name='dashboard_social_links'),
    path('social-links/add/', views.dashboard_add_social_link, name='dashboard_add_social_link'),
    path('social-links/edit/<str:pk>/', views.dashboard_edit_social_link, name='dashboard_edit_social_link'),
    path('social-links/delete/<str:pk>/', views.dashboard_delete_social_link, name='dashboard_delete_social_link'),

    # Comment moderation
    path('comments/', views.dashboard_comments, name='dashboard_comments'),
    path('comments/<str:pk>/', views.dashboard_comment_detail, name='dashboard_comment_detail'),
    path('comments/<str:pk>/approve/', views.dashboard_comment_approve, name='dashboard_comment_approve'),
    path('comments/<str:pk>/unapprove/', views.dashboard_comment_unapprove, name='dashboard_comment_unapprove'),
    path('comments/delete/<str:pk>/', views.dashboard_comment_delete, name='dashboard_comment_delete'),
]
