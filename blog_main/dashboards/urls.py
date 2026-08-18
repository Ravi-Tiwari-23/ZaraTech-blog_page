from django.urls import path
from .import views

urlpatterns = [
    path('', views.dashboards, name='dashboard'),
    path('categories/', views.categories, name = 'categories'),
]