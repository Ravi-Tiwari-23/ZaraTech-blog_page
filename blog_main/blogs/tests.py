from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.template.loader import render_to_string
from django.test import RequestFactory

from .models import Blog, Category, Comment


class BlogFeatureTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(category_name='Django')
        self.author = User.objects.create_user('author', password='test-pass-123')
        self.post = Blog.objects.create(
            title='A useful Django post',
            Category=self.category,
            author=self.author,
            short_description='Short description',
            blog_body='Body copy for the article.',
            status='Published',
        )

    def test_slug_is_unique_and_stable(self):
        duplicate = Blog.objects.create(
            title=self.post.title,
            Category=self.category,
            author=self.author,
            short_description='Another description',
            blog_body='Another body',
        )
        self.assertEqual(self.post.slug, 'a-useful-django-post')
        self.assertEqual(duplicate.slug, 'a-useful-django-post-1')

        original_slug = self.post.slug
        self.post.title = 'A completely new title'
        self.post.save()
        self.assertEqual(self.post.slug, original_slug)

    def test_view_count_increments_once_per_session(self):
        url = reverse('blogs', args=[self.post.slug])
        self.client.get(url)
        self.client.get(url)
        self.post.refresh_from_db()
        self.assertEqual(self.post.views, 1)

    def test_only_authenticated_users_can_comment(self):
        url = reverse('blogs', args=[self.post.slug])
        response = self.client.post(url, {'body': 'Anonymous comment'})
        self.assertRedirects(response, f"{reverse('login')}?next={url}", fetch_redirect_response=False)
        self.assertEqual(Comment.objects.count(), 0)

        self.client.login(username='author', password='test-pass-123')
        response = self.client.post(url, {'body': 'Authenticated comment'})
        self.assertRedirects(response, f'{url}#comments', fetch_redirect_response=False)
        self.assertTrue(Comment.objects.filter(body='Authenticated comment').exists())

    def test_article_has_canonical_social_and_structured_metadata(self):
        response = self.client.get(reverse('blogs', args=[self.post.slug]))

        self.assertContains(response, '<link rel="canonical"', html=False)
        self.assertContains(response, 'application/ld+json')
        self.assertContains(response, 'article:published_time')

    def test_sitemap_only_includes_published_articles(self):
        draft = Blog.objects.create(
            title='Private draft',
            Category=self.category,
            author=self.author,
            short_description='Not ready',
            blog_body='Draft body',
            status='Draft',
        )

        response = self.client.get(reverse('django.contrib.sitemaps.views.sitemap'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('blogs', args=[self.post.slug]))
        self.assertNotContains(response, reverse('blogs', args=[draft.slug]))

    def test_robots_and_error_templates_are_safe(self):
        robots = self.client.get(reverse('robots_txt'))
        rendered_500 = render_to_string('500.html')

        self.assertContains(robots, 'Allow: /')
        self.assertContains(robots, 'Disallow: /dashboard/')
        self.assertIn('Something unexpected happened', rendered_500)
        self.assertNotIn('traceback', rendered_500.lower())

    def test_custom_500_is_branded_and_safe(self):
        from blog_main.views import custom_500

        response = custom_500(RequestFactory().get('/broken/'))

        self.assertEqual(response.status_code, 500)
        self.assertIn(b'GenVilla Insights', response.content)
        self.assertNotIn(b'traceback', response.content.lower())

    @override_settings(DEBUG=False)
    def test_custom_404_is_branded(self):
        response = self.client.get('/this-page-does-not-exist/')

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Page not found | GenVilla Insights', status_code=404)
        self.assertContains(response, 'Search articles', status_code=404)


class DashboardPermissionTests(TestCase):
    def setUp(self):
        manager_group = Group.objects.get(name='Manager')
        editor_group = Group.objects.get(name='Editor')
        self.manager = User.objects.create_user('manager', password='test-pass-123')
        self.manager.groups.add(manager_group)
        self.editor = User.objects.create_user('editor', password='test-pass-123')
        self.editor.groups.add(editor_group)
        self.other_editor = User.objects.create_user('other', password='test-pass-123')
        self.other_editor.groups.add(editor_group)
        self.category = Category.objects.create(category_name='Python')
        self.other_post = Blog.objects.create(
            title='Other editor post',
            Category=self.category,
            author=self.other_editor,
            short_description='Description',
            blog_body='Article body',
        )

    def test_editor_cannot_access_manager_pages(self):
        self.client.login(username='editor', password='test-pass-123')
        self.assertEqual(self.client.get(reverse('categories')).status_code, 403)
        self.assertEqual(self.client.get(reverse('users')).status_code, 403)

    def test_editor_cannot_edit_another_authors_post(self):
        self.client.login(username='editor', password='test-pass-123')
        response = self.client.get(reverse('edit_post', args=[self.other_post.pk]))
        self.assertEqual(response.status_code, 404)

    def test_manager_can_manage_categories_users_and_all_posts(self):
        self.client.login(username='manager', password='test-pass-123')
        self.assertEqual(self.client.get(reverse('categories')).status_code, 200)
        self.assertEqual(self.client.get(reverse('users')).status_code, 200)
        self.assertEqual(
            self.client.get(reverse('edit_post', args=[self.other_post.pk])).status_code,
            200,
        )
