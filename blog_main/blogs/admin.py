from django.contrib import admin
from .models import Category, Blog, Comment

class BlogAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug' : ('title',)}
    list_display = ('title', 'Category', 'author', 'status', 'is_featured', 'views')
    search_fields = ('id', 'title', 'Category__category_name', 'status')
    list_editable =('is_featured',)

admin.site.register(Category)
admin.site.register(Blog , BlogAdmin)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'blog', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('body', 'user__username', 'blog__title')
    list_editable = ('is_approved',)
