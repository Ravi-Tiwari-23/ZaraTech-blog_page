from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.contrib.messages import get_messages
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .utils import OTP_MAX_ATTEMPTS


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="GenVilla <security@example.test>",
)
class OTPAccountFlowTests(TestCase):
    password = "Original-Secure-Password-2026!"
    new_password = "New-Secure-Password-2026!"

    def setUp(self):
        self.user = User.objects.create_user(
            username="reader",
            email="reader@example.test",
            password=self.password,
            is_active=True,
        )

    def _messages(self, response):
        return [str(message) for message in get_messages(response.wsgi_request)]

    def _request_reset(self, email=None, otp="123456", follow=False):
        with patch("accounts.utils.generate_otp", return_value=otp):
            return self.client.post(
                reverse("forgot_password"),
                {"email": email or self.user.email},
                follow=follow,
            )

    def test_registration_verification_receives_server_countdown(self):
        session = self.client.session
        session["email_verification_email"] = "pending@example.test"
        session["email_verification_last_sent"] = timezone.now().timestamp()
        session.save()

        response = self.client.get(reverse("verify_email"))

        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.context["resend_wait"], 0)
        self.assertLessEqual(response.context["resend_wait"], 60)
        self.assertContains(response, "You can resend the code in")
        self.assertContains(response, 'id="resendButton" disabled')

    def test_registration_keeps_inactive_reader_otp_flow(self):
        Group.objects.get_or_create(name="Reader")

        with patch("accounts.utils.generate_otp", return_value="654321"):
            response = self.client.post(
                reverse("register"),
                {
                    "email": "new-reader@example.test",
                    "username": "new-reader",
                    "password1": "Brand-New-Reader-Password-2026!",
                    "password2": "Brand-New-Reader-Password-2026!",
                },
            )

        self.assertRedirects(response, reverse("verify_email"))
        user = User.objects.get(username="new-reader")
        self.assertFalse(user.is_active)
        self.assertTrue(user.groups.filter(name="Reader").exists())
        self.assertEqual(len(mail.outbox), 1)
        session = self.client.session
        self.assertEqual(
            session["email_verification_email"],
            "new-reader@example.test",
        )
        self.assertNotEqual(
            session["email_verification_otp_hash"],
            "654321",
        )

    def test_login_redirect_rules_remain_unchanged(self):
        next_response = self.client.post(
            f'{reverse("login")}?next=/about/',
            {"username": self.user.username, "password": self.password},
        )
        self.assertRedirects(
            next_response,
            "/about/",
            fetch_redirect_response=False,
        )

        self.client.logout()
        manager = User.objects.create_user(
            username="manager",
            email="manager@example.test",
            password=self.password,
        )
        manager_group, _ = Group.objects.get_or_create(name="Manager")
        manager.groups.add(manager_group)

        manager_response = self.client.post(
            reverse("login"),
            {"username": manager.username, "password": self.password},
        )
        self.assertRedirects(
            manager_response,
            reverse("dashboard"),
            fetch_redirect_response=False,
        )

    def test_password_reset_request_sends_hashed_otp_for_active_user(self):
        response = self._request_reset()

        self.assertRedirects(response, reverse("verify_reset_otp"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("123456", mail.outbox[0].body)

        session = self.client.session
        self.assertNotEqual(session["password_reset_otp_hash"], "123456")
        self.assertEqual(session["password_reset_email"], self.user.email)
        self.assertEqual(session["password_reset_attempts"], 0)
        self.assertIn("password_reset_expires_at", session)
        self.assertIn("password_reset_last_sent", session)

    def test_unknown_and_inactive_emails_get_generic_response_without_email(self):
        unknown_response = self._request_reset(
            "unknown@example.test",
            follow=True,
        )
        unknown_messages = self._messages(unknown_response)

        inactive = User.objects.create_user(
            username="inactive",
            email="inactive@example.test",
            password=self.password,
            is_active=False,
        )
        inactive_response = self._request_reset(
            inactive.email,
            follow=True,
        )
        inactive_messages = self._messages(inactive_response)

        self.assertRedirects(unknown_response, reverse("verify_reset_otp"))
        self.assertRedirects(inactive_response, reverse("verify_reset_otp"))
        self.assertEqual(unknown_messages, inactive_messages)
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(User.objects.get(pk=inactive.pk).is_active)

    def test_early_resend_is_rejected_by_server_and_keeps_challenge(self):
        self._request_reset()
        session = self.client.session
        original_hash = session["password_reset_otp_hash"]
        original_last_sent = session["password_reset_last_sent"]

        response = self.client.post(reverse("resend_password_reset_otp"))

        self.assertRedirects(response, reverse("verify_reset_otp"))
        self.assertEqual(len(mail.outbox), 1)
        session = self.client.session
        self.assertEqual(session["password_reset_otp_hash"], original_hash)
        self.assertEqual(
            session["password_reset_last_sent"],
            original_last_sent,
        )

    def test_resend_replaces_old_otp(self):
        self._request_reset(otp="111111")
        session = self.client.session
        session["password_reset_last_sent"] = (
            timezone.now().timestamp() - 61
        )
        session.save()

        with patch("accounts.utils.generate_otp", return_value="222222"):
            resend_response = self.client.post(
                reverse("resend_password_reset_otp"),
            )

        self.assertRedirects(resend_response, reverse("verify_reset_otp"))
        self.assertEqual(len(mail.outbox), 2)

        old_response = self.client.post(
            reverse("verify_reset_otp"),
            {"otp": "111111"},
        )
        self.assertEqual(old_response.status_code, 200)

        new_response = self.client.post(
            reverse("verify_reset_otp"),
            {"otp": "222222"},
        )
        self.assertRedirects(new_response, reverse("reset_password"))

    def test_verified_otp_allows_password_change_and_clears_session(self):
        self._request_reset()

        verify_response = self.client.post(
            reverse("verify_reset_otp"),
            {"otp": "123456"},
        )
        self.assertRedirects(verify_response, reverse("reset_password"))

        session = self.client.session
        self.assertTrue(session["password_reset_verified"])
        self.assertNotIn("password_reset_otp_hash", session)

        reset_response = self.client.post(
            reverse("reset_password"),
            {
                "new_password1": self.new_password,
                "new_password2": self.new_password,
            },
        )

        self.assertRedirects(reset_response, reverse("login"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))
        self.assertFalse(self.user.check_password(self.password))
        self.assertFalse(
            self.client.login(
                username=self.user.username,
                password=self.password,
            )
        )
        self.assertTrue(
            self.client.login(
                username=self.user.username,
                password=self.new_password,
            )
        )
        session = self.client.session
        self.assertNotIn("password_reset_verified", session)
        self.assertNotIn("password_reset_verified_email", session)

    def test_expired_and_max_attempt_challenges_are_cleared(self):
        self._request_reset()
        session = self.client.session
        session["password_reset_expires_at"] = (
            timezone.now().timestamp() - 1
        )
        session.save()

        expired_response = self.client.post(
            reverse("verify_reset_otp"),
            {"otp": "123456"},
        )
        self.assertEqual(expired_response.status_code, 200)
        self.assertNotIn("password_reset_otp_hash", self.client.session)

        self._request_reset()
        for _ in range(OTP_MAX_ATTEMPTS):
            max_attempt_response = self.client.post(
                reverse("verify_reset_otp"),
                {"otp": "000000"},
            )

        self.assertEqual(max_attempt_response.status_code, 200)
        self.assertNotIn("password_reset_otp_hash", self.client.session)

    def test_sensitive_routes_require_post_or_verified_session(self):
        self.assertEqual(
            self.client.get(reverse("resend_email_verification")).status_code,
            405,
        )
        self.assertEqual(
            self.client.get(reverse("resend_password_reset_otp")).status_code,
            405,
        )
        response = self.client.get(reverse("reset_password"))
        self.assertRedirects(response, reverse("forgot_password"))
