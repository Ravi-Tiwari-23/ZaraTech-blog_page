from datetime import timedelta
from urllib.parse import urlsplit

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from blogs.models import Blog, Category
from .forms import RegistrationForm


@override_settings(
    ALLOWED_HOSTS=["blog.genvilla.in"],
    SECURE_SSL_REDIRECT=True,
)
class HealthCheckTests(TestCase):
    def test_internal_http_health_check_bypasses_private_ip_host_validation(self):
        response = self.client.get(
            reverse("healthz"),
            secure=False,
            HTTP_HOST="172.31.30.16:8000",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "service": "zaratech-blog"},
        )


@override_settings(GENVILLA_BLOG_API_KEY="test-api-key")
class PostsApiTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(category_name="API")
        self.author = User.objects.create_user(
            "api-author",
            email="private@example.com",
            password="private-password",
            first_name="Public",
            last_name="Author",
        )
        self.url = reverse("posts_api")

    def create_post(self, title, *, status="Published", image=""):
        return Blog.objects.create(
            title=title,
            Category=self.category,
            author=self.author,
            featured_image=image,
            short_description="<strong>Public</strong> description",
            blog_body="Private full article body",
            status=status,
        )

    def authorized_get(self):
        return self.client.get(self.url, HTTP_X_API_KEY="test-api-key")

    def test_correct_api_key_returns_public_post_fields(self):
        post = self.create_post("Published article")

        response = self.authorized_get()

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(list(payload), ["posts"])
        self.assertEqual(len(payload["posts"]), 1)
        item = payload["posts"][0]
        self.assertEqual(
            set(item),
            {
                "title",
                "slug",
                "description",
                "author",
                "image",
                "published_at",
                "updated_at",
                "url",
            },
        )
        self.assertEqual(item["title"], post.title)
        self.assertEqual(item["slug"], post.slug)
        self.assertEqual(item["description"], "Public description")
        self.assertEqual(item["author"], "Public Author")
        self.assertIsNone(item["image"])
        self.assertEqual(urlsplit(item["url"]).scheme, "https")
        self.assertEqual(urlsplit(item["url"]).netloc, "zaratech-blog.vercel.app")
        self.assertEqual(
            urlsplit(item["url"]).path,
            reverse("blogs", args=[post.slug]),
        )
        self.assertEqual(item["published_at"], post.created_at.isoformat())
        self.assertEqual(item["updated_at"], post.updated_at.isoformat())

        serialized = response.content.decode()
        for private_value in (
            self.author.email,
            self.author.password,
            "Private full article body",
            "test-api-key",
        ):
            self.assertNotIn(private_value, serialized)
        self.assertTrue(
            {
                "id",
                "user_id",
                "email",
                "password",
                "groups",
                "permissions",
                "is_active",
                "blog_body",
            }.isdisjoint(item)
        )

    def test_missing_api_key_is_unauthorized(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "Unauthorized"})

    def test_incorrect_api_key_is_unauthorized(self):
        response = self.client.get(self.url, HTTP_X_API_KEY="wrong-key")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "Unauthorized"})

    @override_settings(GENVILLA_BLOG_API_KEY=None)
    def test_missing_server_key_fails_closed(self):
        response = self.client.get(self.url, HTTP_X_API_KEY="test-api-key")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"error": "Service unavailable"})

    @override_settings(GENVILLA_BLOG_API_KEY="")
    def test_empty_server_key_fails_closed_when_request_key_is_missing(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"error": "Service unavailable"})

    def test_only_published_posts_are_returned(self):
        published = self.create_post("Visible article")
        draft = self.create_post("Private draft", status="Draft")

        response = self.authorized_get()
        slugs = [item["slug"] for item in response.json()["posts"]]

        self.assertIn(published.slug, slugs)
        self.assertNotIn(draft.slug, slugs)

    def test_posts_are_newest_first_and_limited_to_ten(self):
        start = timezone.now() - timedelta(days=20)
        posts = [self.create_post(f"Article {index}") for index in range(12)]
        for index, post in enumerate(posts):
            Blog.objects.filter(pk=post.pk).update(
                created_at=start + timedelta(days=index)
            )

        response = self.authorized_get()
        returned_slugs = [item["slug"] for item in response.json()["posts"]]

        self.assertEqual(len(returned_slugs), 10)
        self.assertEqual(
            returned_slugs,
            [post.slug for post in reversed(posts[2:])],
        )

    def test_featured_image_is_returned_as_a_usable_url(self):
        self.create_post("Image article", image="uploads/api-image.jpg")

        item = self.authorized_get().json()["posts"][0]

        self.assertEqual(
            item["image"],
            "https://zaratech-blog.vercel.app/media/uploads/api-image.jpg",
        )

    def test_post_is_not_accepted(self):
        response = self.client.post(
            self.url,
            HTTP_X_API_KEY="test-api-key",
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response["Allow"], "GET")

    def test_health_endpoint_remains_unaffected(self):
        response = self.client.get(reverse("healthz"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "service": "zaratech-blog"},
        )


class RegistrationFormTests(TestCase):
    def test_username_limit_is_enforced_server_side(self):
        form = RegistrationForm(data={
            'email': 'reader@example.com',
            'username': 'a' * 21,
            'password1': 'A-strong-passphrase-2048',
            'password2': 'A-strong-passphrase-2048',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('Ensure this value has at most 20 characters', form.errors['username'][0])

    def test_registration_help_matches_enabled_validators(self):
        form = RegistrationForm()

        self.assertIn('20 characters or fewer', form.fields['username'].help_text)
        self.assertEqual(form.fields['username'].widget.attrs['maxlength'], '20')
        self.assertNotIn('similar to your other personal information', form.fields['password1'].help_text)

    def test_username_is_independent_from_email(self):
        form = RegistrationForm(data={
            'email': 'email-name@example.com',
            'username': 'chosen-name',
            'password1': 'A-strong-passphrase-2048',
            'password2': 'A-strong-passphrase-2048',
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['username'], 'chosen-name')

    def test_registration_page_has_password_controls(self):
        response = self.client.get(reverse('register'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'password-toggle')
        self.assertNotContains(response, 'follow the topics')
