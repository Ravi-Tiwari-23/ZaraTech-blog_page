from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.template.loader import render_to_string
from django.test import RequestFactory

from dashboards.forms import BlogPostForm
from .models import Blog, Category, Comment, SavedPost


class BlogFeatureTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(category_name='Django')
        self.author = User.objects.create_user(
            'author',
            password='test-pass-123',
            first_name='Ravi',
            last_name='Tiwari',
        )
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

    def test_blog_cards_show_author_name_instead_of_reading_time(self):
        response = self.client.get(
            reverse('posts_by_category', args=[self.category.pk])
        )

        self.assertContains(response, 'Ravi Tiwari')
        self.assertNotContains(response, '1 min read')

    def test_save_persists_across_refresh_and_duplicate_post_is_idempotent(self):
        self.client.login(username='author', password='test-pass-123')
        save_url = reverse('save_blog', args=[self.post.slug])

        self.client.post(save_url)
        self.client.post(save_url)

        self.assertEqual(
            SavedPost.objects.filter(
                user=self.author,
                blog=self.post,
            ).count(),
            1,
        )
        refreshed = self.client.get(
            reverse('posts_by_category', args=[self.category.pk])
        )
        self.assertContains(refreshed, 'aria-label="Remove saved article"')
        self.assertContains(refreshed, 'fa-bookmark')

    def test_user_can_unsave_article(self):
        SavedPost.objects.create(user=self.author, blog=self.post)
        self.client.login(username='author', password='test-pass-123')

        response = self.client.post(
            reverse('unsave_blog', args=[self.post.slug])
        )

        self.assertRedirects(
            response,
            reverse('blogs', args=[self.post.slug]),
            fetch_redirect_response=False,
        )
        self.assertFalse(
            SavedPost.objects.filter(
                user=self.author,
                blog=self.post,
            ).exists()
        )

    def test_saved_articles_are_private_to_each_user(self):
        SavedPost.objects.create(user=self.author, blog=self.post)
        second_user = User.objects.create_user(
            'second-reader',
            password='test-pass-123',
        )

        self.client.login(username='second-reader', password='test-pass-123')
        response = self.client.get(reverse('saved_posts'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.post.title)
        self.assertEqual(
            SavedPost.objects.filter(user=second_user).count(),
            0,
        )

        self.client.logout()
        self.client.login(username='author', password='test-pass-123')
        response = self.client.get(reverse('saved_posts'))
        self.assertContains(response, self.post.title)

    def test_anonymous_save_and_saved_page_redirect_to_login(self):
        save_url = reverse('save_blog', args=[self.post.slug])
        saved_url = reverse('saved_posts')

        save_response = self.client.post(save_url)
        saved_response = self.client.get(saved_url)

        self.assertRedirects(
            save_response,
            f'{reverse("login")}?next={save_url}',
            fetch_redirect_response=False,
        )
        self.assertRedirects(
            saved_response,
            f'{reverse("login")}?next={saved_url}',
            fetch_redirect_response=False,
        )

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

    def test_article_renders_supported_formatting_and_escapes_unsafe_html(self):
        self.post.blog_body = (
            '## Useful heading\n\n**Bold** and *italic*.\n\n'
            '- First item\n- Second item\n\n1. Step one\n2. Step two\n\n'
            '[Safe link](https://example.com)\n\n'
            '<script>alert("unsafe")</script>\n\n'
            '[Bad link](javascript:alert(1))'
        )
        self.post.save(update_fields=['blog_body'])

        response = self.client.get(reverse('blogs', args=[self.post.slug]))

        self.assertContains(response, '<h2>Useful heading</h2>', html=False)
        self.assertContains(response, '<strong>Bold</strong>', html=False)
        self.assertContains(response, '<em>italic</em>', html=False)
        self.assertContains(response, '<ul><li>First item</li><li>Second item</li></ul>', html=False)
        self.assertContains(response, '<ol><li>Step one</li><li>Step two</li></ol>', html=False)
        self.assertContains(response, 'href="https://example.com"', html=False)
        self.assertContains(response, '&lt;script&gt;', html=False)
        self.assertNotContains(response, '<script>alert', html=False)
        self.assertNotContains(response, 'href="javascript:', html=False)

    def test_blog_body_form_accepts_long_articles_up_to_ten_thousand(self):
        field = BlogPostForm().fields['blog_body']

        self.assertEqual(Blog._meta.get_field('blog_body').max_length, 10000)
        self.assertEqual(field.max_length, 10000)
        self.assertEqual(len(field.clean('x' * 6000)), 6000)
        with self.assertRaisesMessage(ValidationError, 'at most 10000 characters'):
            field.clean('x' * 10001)

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

    def test_add_and_edit_pages_include_editor_and_existing_content(self):
        self.client.login(username='other', password='test-pass-123')

        add_response = self.client.get(reverse('add_post'))
        edit_response = self.client.get(
            reverse('edit_post', args=[self.other_post.pk])
        )

        self.assertContains(add_response, 'data-blog-editor-toolbar')
        self.assertContains(edit_response, 'data-blog-editor-toolbar')
        self.assertContains(edit_response, self.other_post.blog_body)

    def test_long_formatted_article_saves_and_reloads_through_edit_view(self):
        self.client.login(username='other', password='test-pass-123')
        self.other_post.featured_image = 'uploads/existing.jpg'
        self.other_post.save(update_fields=['featured_image'])
        formatted_prefix = (
            '## Heading\n\n**Bold** and *italic*.\n\n'
            '- Bullet\n\n1. Numbered\n\n'
            '[Link](https://example.com)\n\n'
        )
        body = formatted_prefix + ('x' * (6000 - len(formatted_prefix)))

        response = self.client.post(
            reverse('edit_post', args=[self.other_post.pk]),
            {
                'title': self.other_post.title,
                'Category': self.category.pk,
                'short_description': self.other_post.short_description,
                'blog_body': body,
                'status': 'Published',
                'is_featured': '',
            },
        )

        self.assertRedirects(response, reverse('posts'))
        self.other_post.refresh_from_db()
        self.assertEqual(self.other_post.blog_body, body)
        reload_response = self.client.get(
            reverse('edit_post', args=[self.other_post.pk])
        )
        self.assertContains(reload_response, body)
