from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email',
            'inputmode': 'email',
        }),
    )
    username = forms.CharField(
        max_length=20,
        help_text=(
            'Required. 20 characters or fewer. '
            'Letters, digits and @/./+/-/_ only.'
        ),
        widget=forms.TextInput(attrs={
            'autocomplete': 'username',
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
