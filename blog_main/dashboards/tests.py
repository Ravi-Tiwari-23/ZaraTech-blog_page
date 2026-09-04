from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from assignments.models import About, SocialLink
from blogs.models import Blog, Category, Comment


class DashboardManagementTestCase(TestCase):
    password = 'test-pass-123'

    def setUp(self):
        manager_group, _ = Group.objects.get_or_create(name='Manager')
        editor_group, _ = Group.objects.get_or_create(name='Editor')

        self.manager = User.objects.create_user('manager', password=self.password)
        self.manager.groups.add(manager_group)
        self.editor = User.objects.create_user('editor', password=self.password)
        self.editor.groups.add(editor_group)
        self.reader = User.objects.create_user('reader', password=self.password)
        self.superuser = User.objects.create_superuser(
            'superuser',
            'superuser@example.com',
            self.password,
        )

        self.category = Category.objects.create(category_name='Property Guides')
        self.post = Blog.objects.create(
            title='A published property guide',
            Category=self.category,
            author=self.editor,
            short_description='A useful guide.',
            blog_body='A complete article body.',
            status='Published',
        )
        self.approved_comment = Comment.objects.create(
            blog=self.post,
            user=self.reader,
            body='Approved public comment.',
            is_approved=True,
        )
        self.unapproved_comment = Comment.objects.create(
            blog=self.post,
            user=self.reader,
            body='Private unapproved comment.',
            is_approved=False,
        )

    def login(self, user):
        self.client.force_login(user)


class DashboardPermissionTests(DashboardManagementTestCase):
    protected_pages = (
        'dashboard_about',
        'dashboard_social_links',
        'dashboard_comments',
    )

    def test_anonymous_users_are_redirected_to_login(self):
        for name in self.protected_pages:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse('login'), response.url)

    def test_reader_is_denied_management_pages(self):
        self.login(self.reader)
        for name in self.protected_pages:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)

    def test_editor_can_access_management_pages_but_cannot_delete_comments(self):
        self.login(self.editor)
        for name in self.protected_pages:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

        delete_url = reverse(
            'dashboard_comment_delete',
            args=[str(self.approved_comment.pk)],
        )
        self.assertEqual(self.client.get(delete_url).status_code, 403)
        self.assertEqual(self.client.post(delete_url).status_code, 403)
        self.assertTrue(Comment.objects.filter(pk=self.approved_comment.pk).exists())

    def test_manager_and_superuser_have_full_access(self):
        for user in (self.manager, self.superuser):
            self.login(user)
            with self.subTest(user=user.username):
                self.assertEqual(
                    self.client.get(reverse('dashboard_about')).status_code,
                    200,
                )
                self.assertEqual(
                    self.client.get(reverse('dashboard_social_links')).status_code,
                    200,
                )
                self.assertEqual(
                    self.client.get(reverse('dashboard_comments')).status_code,
                    200,
                )
                self.assertEqual(
                    self.client.get(reverse(
                        'dashboard_comment_delete',
                        args=[str(self.approved_comment.pk)],
                    )).status_code,
                    200,
                )
            self.client.logout()

    def test_sidebar_exposes_new_sections_to_dashboard_users(self):
        self.login(self.editor)
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, reverse('dashboard_about'))
        self.assertContains(response, reverse('dashboard_social_links'))
        self.assertContains(response, reverse('dashboard_comments'))


class AboutManagementTests(DashboardManagementTestCase):
    def test_existing_about_record_is_updated_without_creating_a_duplicate(self):
        about = About.objects.create(
            about_heading='Original heading',
            about_description='Original description',
        )
        self.login(self.editor)

        response = self.client.post(reverse('dashboard_about'), {
            'about_heading': 'Updated heading',
            'about_description': 'Updated public description',
        })

        self.assertRedirects(response, reverse('dashboard_about'))
        self.assertEqual(About.objects.count(), 1)
        about.refresh_from_db()
        self.assertEqual(about.about_heading, 'Updated heading')
        self.assertEqual(about.about_description, 'Updated public description')

        public_response = self.client.get(reverse('home'))
        self.assertContains(public_response, 'Updated heading')
        self.assertContains(public_response, 'Updated public description')

    def test_first_about_record_can_be_created(self):
        self.login(self.manager)
        response = self.client.post(reverse('dashboard_about'), {
            'about_heading': 'Our approach',
            'about_description': 'Clear property guidance.',
        })

        self.assertRedirects(response, reverse('dashboard_about'))
        self.assertEqual(About.objects.count(), 1)

    def test_multiple_records_are_reported_and_not_deleted(self):
        About.objects.create(about_heading='Older', about_description='Older copy')
        newest = About.objects.create(
            about_heading='Newest',
            about_description='Newest copy',
        )
        self.login(self.manager)

        response = self.client.get(reverse('dashboard_about'))

        self.assertContains(response, 'Multiple About records exist')
        self.assertEqual(response.context['about'], newest)
        self.assertEqual(About.objects.count(), 2)


class SocialLinkManagementTests(DashboardManagementTestCase):
    def setUp(self):
        super().setUp()
        self.social_link = SocialLink.objects.create(
            platform='LinkedIn',
            link='https://www.linkedin.com/company/genvilla/',
        )
        self.login(self.editor)

    def test_social_links_are_listed(self):
        response = self.client.get(reverse('dashboard_social_links'))
        self.assertContains(response, 'LinkedIn')
        self.assertContains(response, self.social_link.link)

    def test_add_validates_url_and_creates_valid_link(self):
        add_url = reverse('dashboard_add_social_link')
        invalid_response = self.client.post(add_url, {
            'platform': 'Invalid',
            'link': 'not-a-url',
        })
        self.assertEqual(invalid_response.status_code, 200)
        self.assertContains(invalid_response, 'Enter a valid URL')
        self.assertFalse(SocialLink.objects.filter(platform='Invalid').exists())

        valid_response = self.client.post(add_url, {
            'platform': 'GitHub',
            'link': 'https://github.com/genvilla',
        })
        self.assertRedirects(valid_response, reverse('dashboard_social_links'))
        self.assertTrue(SocialLink.objects.filter(platform='GitHub').exists())

    def test_edit_uses_string_compatible_primary_key(self):
        response = self.client.post(reverse(
            'dashboard_edit_social_link',
            args=[str(self.social_link.pk)],
        ), {
            'platform': 'LinkedIn Company',
            'link': 'https://www.linkedin.com/company/genvilla-insights/',
        })

        self.assertRedirects(response, reverse('dashboard_social_links'))
        self.social_link.refresh_from_db()
        self.assertEqual(self.social_link.platform, 'LinkedIn Company')

    def test_delete_requires_confirmation_and_post(self):
        delete_url = reverse(
            'dashboard_delete_social_link',
            args=[str(self.social_link.pk)],
        )
        get_response = self.client.get(delete_url)
        self.assertEqual(get_response.status_code, 200)
        self.assertContains(get_response, 'LinkedIn')
        self.assertTrue(SocialLink.objects.filter(pk=self.social_link.pk).exists())

        post_response = self.client.post(delete_url)
        self.assertRedirects(post_response, reverse('dashboard_social_links'))
        self.assertFalse(SocialLink.objects.filter(pk=self.social_link.pk).exists())


class CommentManagementTests(DashboardManagementTestCase):
    def setUp(self):
        super().setUp()
        self.login(self.editor)

    def test_list_filters_and_detail_show_full_escaped_comment(self):
        approved_response = self.client.get(
            reverse('dashboard_comments'),
            {'status': 'approved'},
        )
        self.assertContains(approved_response, self.approved_comment.body)
        self.assertNotContains(approved_response, self.unapproved_comment.body)

        unapproved_response = self.client.get(
            reverse('dashboard_comments'),
            {'status': 'unapproved'},
        )
        self.assertContains(unapproved_response, self.unapproved_comment.body)
        self.assertNotContains(unapproved_response, self.approved_comment.body)

        self.unapproved_comment.body = '<script>alert("unsafe")</script>'
        self.unapproved_comment.save()
        detail_response = self.client.get(reverse(
            'dashboard_comment_detail',
            args=[str(self.unapproved_comment.pk)],
        ))
        self.assertContains(detail_response, '&lt;script&gt;', html=False)
        self.assertNotContains(detail_response, '<script>alert')

    def test_approve_and_unapprove_are_post_only(self):
        approve_url = reverse(
            'dashboard_comment_approve',
            args=[str(self.unapproved_comment.pk)],
        )
        unapprove_url = reverse(
            'dashboard_comment_unapprove',
            args=[str(self.approved_comment.pk)],
        )
        self.assertEqual(self.client.get(approve_url).status_code, 405)
        self.assertEqual(self.client.get(unapprove_url).status_code, 405)

        self.assertRedirects(
            self.client.post(approve_url),
            reverse('dashboard_comments'),
        )
        self.unapproved_comment.refresh_from_db()
        self.assertTrue(self.unapproved_comment.is_approved)

        self.assertRedirects(
            self.client.post(unapprove_url),
            reverse('dashboard_comments'),
        )
        self.approved_comment.refresh_from_db()
        self.assertFalse(self.approved_comment.is_approved)

    def test_public_article_only_shows_approved_comments(self):
        response = self.client.get(reverse('blogs', args=[self.post.slug]))
        self.assertContains(response, self.approved_comment.body)
        self.assertNotContains(response, self.unapproved_comment.body)

    def test_comments_are_paginated_twenty_per_page(self):
        for number in range(20):
            Comment.objects.create(
                blog=self.post,
                user=self.reader,
                body=f'Additional comment {number}',
            )

        response = self.client.get(reverse('dashboard_comments'))
        self.assertEqual(response.context['page_obj'].paginator.per_page, 20)
        self.assertEqual(len(response.context['page_obj']), 20)
        self.assertTrue(response.context['page_obj'].has_next())

    def test_manager_delete_requires_confirmation_and_post(self):
        self.client.logout()
        self.login(self.manager)
        delete_url = reverse(
            'dashboard_comment_delete',
            args=[str(self.approved_comment.pk)],
        )

        get_response = self.client.get(delete_url)
        self.assertEqual(get_response.status_code, 200)
        self.assertContains(get_response, self.approved_comment.body)
        self.assertTrue(Comment.objects.filter(pk=self.approved_comment.pk).exists())

        post_response = self.client.post(delete_url)
        self.assertRedirects(post_response, reverse('dashboard_comments'))
        self.assertFalse(Comment.objects.filter(pk=self.approved_comment.pk).exists())
