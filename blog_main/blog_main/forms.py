from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email',
            'inputmode': 'email',
        }),
    )
    username = forms.CharField(
        label='Choose a username',
        max_length=20,
        help_text=(
            'Required. 20 characters or fewer. '
            'Letters, digits and @/./+/-/_ only.'
        ),
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'placeholder': 'Choose a username',
            'autocapitalize': 'none',
            'spellcheck': 'false',
            'maxlength': '20',
        }),
    )

    class Meta:
        model = User
        fields = ('email', 'username', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['password1'].help_text = (
            password_validation.password_validators_help_text_html()
        )
        self.fields['email'].widget.attrs.update({
            'autocomplete': 'email',
            'inputmode': 'email',
        })
        self.fields['password1'].widget.attrs['autocomplete'] = 'new-password'
        self.fields['password2'].widget.attrs['autocomplete'] = 'new-password'

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email


class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email or username'
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Email or username',
            'autocomplete': 'username',
            'autocapitalize': 'none',
            'spellcheck': 'false',
        })
        # Email addresses can be longer than the username model field.
        self.fields['username'].max_length = 254
        self.fields['username'].widget.attrs['maxlength'] = 254

    def clean_username(self):
        identifier = self.cleaned_data['username']
        try:
            user = User.objects.get(email__iexact=identifier)
        except User.DoesNotExist:
            return identifier
        except User.MultipleObjectsReturned:
            # Never select an arbitrary account when an email is shared.
            raise self.get_invalid_login_error()
        return user.get_username()
