from django.urls import path
from . import views 

urlpatterns = [
    path('category/<str:category_id>/', views.posts_by_category, name='posts_by_category')

]