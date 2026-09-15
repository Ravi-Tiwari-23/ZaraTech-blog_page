from django.test import TestCase
from django.urls import reverse

from .forms import RegistrationForm


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
