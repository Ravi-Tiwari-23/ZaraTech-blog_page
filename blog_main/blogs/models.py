from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class Category(models.Model):
    category_name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add =True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.category_name


STATUS_CHOICES = (
    ("Draft", "Draft"),
    ("Published", "Published")
)


class Blog(models.Model):
    title = models.CharField(max_length=100)

    slug = models.SlugField(max_length=150, unique=True, blank=True)
    Category = models.ForeignKey(Category, on_delete=models.CASCADE)

    author = models.ForeignKey(User, on_delete=models.CASCADE)

    featured_image = models.ImageField(upload_to ='uploads/%Y/%M/%D')

    short_description = models.TextField(max_length=500)

    blog_body = models.TextField(max_length= 2000)

    status = models.CharField(max_length=20, choices = STATUS_CHOICES, default="Draft")

    is_featured = models.BooleanField(default=False)

    views = models.PositiveIntegerField(default=0, editable=False)

    created_at = models.DateTimeField(auto_now_add =True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)

    def save(self, *args, **kwargs):
        """Generate a stable, unique slug without changing it on later edits."""
        if not self.slug:
            base_slug = slugify(self.title)[:130] or 'post'
            candidate = base_slug
            counter = 1
            while Blog.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                suffix = f'-{counter}'
                candidate = f'{base_slug[:150 - len(suffix)]}{suffix}'
                counter += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    @property
    def reading_time(self):
        words = len(self.blog_body.split())
        return max(1, round(words / 200))

    def __str__(self):
        return self.title


class Comment(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_comments')
    body = models.TextField(max_length=1000)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.user.username}: {self.body[:40]}'
