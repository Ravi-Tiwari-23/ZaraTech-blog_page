from django import forms
from django.contrib.auth.forms import (
    PasswordChangeForm,
    SetPasswordForm,
)


class OTPVerificationForm(forms.Form):
    otp = forms.CharField(
        label="Verification code",
        min_length=6,
        max_length=6,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter 6-digit code",
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "maxlength": "6",
            }
        ),
    )

    def clean_otp(self):
        otp = self.cleaned_data["otp"].strip()

        if not otp.isdigit():
            raise forms.ValidationError(
                "Enter a valid 6-digit verification code."
            )

        return otp


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Enter your registered email",
                "autocomplete": "email",
            }
        ),
    )


class GenVillaSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name in ("new_password1", "new_password2"):
            self.fields[field_name].widget.attrs.update(
                {
                    "autocomplete": "new-password",
                    "placeholder": (
                        "Enter a new password"
                        if field_name == "new_password1"
                        else "Confirm your new password"
                    ),
                }
            )


class GenVillaPasswordChangeForm(PasswordChangeForm):
    pass
