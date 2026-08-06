from django.http import HttpResponse
from django.shortcuts import render



def posts_by_category(request, category_id):
    return HttpResponse('Posts by category')

# Create your views here.
