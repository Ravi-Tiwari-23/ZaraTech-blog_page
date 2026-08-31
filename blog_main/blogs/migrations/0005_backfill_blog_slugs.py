from django.db import migrations
from django.utils.text import slugify


def backfill_blog_slugs(apps, schema_editor):
    Blog = apps.get_model('blogs', 'Blog')
    used_slugs = set(
        Blog.objects.exclude(slug='').values_list('slug', flat=True)
    )

    for blog in Blog.objects.filter(slug='').order_by('pk'):
        base_slug = slugify(blog.title)[:130] or 'post'
        candidate = base_slug
        counter = 1
        while candidate in used_slugs:
            suffix = f'-{counter}'
            candidate = f'{base_slug[:150 - len(suffix)]}{suffix}'
            counter += 1
        Blog.objects.filter(pk=blog.pk).update(slug=candidate)
        used_slugs.add(candidate)


class Migration(migrations.Migration):
    dependencies = [
        ('blogs', '0004_alter_blog_options_blog_views_comment'),
    ]

    operations = [
        migrations.RunPython(backfill_blog_slugs, migrations.RunPython.noop),
    ]
