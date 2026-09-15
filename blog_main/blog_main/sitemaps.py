from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from blogs.models import Blog, Category


class StaticViewSitemap(Sitemap):
    protocol = 'https'
    changefreq = 'daily'
    priority = 1.0

    def items(self):
        return ['home']

    def location(self, item):
        return reverse(item)


class BlogSitemap(Sitemap):
    protocol = 'https'
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Blog.objects.filter(status='Published').order_by('-updated_at')

    def lastmod(self, item):
        return item.updated_at

    def location(self, item):
        return reverse('blogs', args=[item.slug])


class CategorySitemap(Sitemap):
    protocol = 'https'
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return Category.objects.all().order_by('category_name')

    def lastmod(self, item):
        return item.updated_at

    def location(self, item):
        return reverse('posts_by_category', args=[str(item.pk)])
