import logging

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .forms import (
    ForgotPasswordForm,
    GenVillaSetPasswordForm,
    OTPVerificationForm,
)
from .utils import (
    can_resend_otp,
    clear_otp_session,
    create_otp_session,
    get_resend_wait_seconds,
    send_otp_email,
    verify_otp,
)


def verify_email(request):
    email = request.session.get(
        "email_verification_email"
    )

    if not email:
        messages.error(
            request,
            "No pending email verification was found."
        )
        return redirect("register")

    if request.method == "POST":
        form = OTPVerificationForm(request.POST)

        if form.is_valid():
            valid, error = verify_otp(
                request,
                "email_verification",
                form.cleaned_data["otp"],
            )

            if valid:
                user = User.objects.filter(
                    email__iexact=email,
                    is_active=False,
                ).first()

                if not user:
                    messages.error(
                        request,
                        "Unable to verify this account."
                    )
                    return redirect("register")

                user.is_active = True
                user.save(update_fields=["is_active"])

                clear_otp_session(
                    request,
                    "email_verification",
                )

                login(request, user)

                messages.success(
                    request,
                    "Your email has been verified successfully."
                )

                return redirect("home")

            messages.error(
                request,
                error,
            )

    else:
        form = OTPVerificationForm()

    return render(
        request,
        "accounts/verify_email.html",
        {
            "form": form,
            "email": email,
            "resend_wait": get_resend_wait_seconds(
                request,
                "email_verification",
            ),
        },
    )


@require_POST
def resend_email_verification(request):
    email = request.session.get(
        "email_verification_email"
    )

    if not email:
        messages.error(
            request,
            "No pending verification was found."
        )
        return redirect("register")

    if not can_resend_otp(
        request,
        "email_verification",
    ):
        messages.warning(
            request,
            "Please wait before requesting another code."
        )
        return redirect("verify_email")

    otp = create_otp_session(
        request,
        "email_verification",
        email,
    )

    try:
        send_otp_email(
            email,
            otp,
            "email_verification",
        )
    except Exception:
        request.session.pop(
            "email_verification_last_sent",
            None,
        )
        request.session.modified = True
        messages.error(
            request,
            "We could not send a new code. Please try again.",
        )
        return redirect("verify_email")

    messages.success(
        request,
        "A new verification code has been sent."
    )

    return redirect("verify_email")


PASSWORD_RESET_PURPOSE = "password_reset"
PASSWORD_RESET_GENERIC_MESSAGE = (
    "If an account exists for that email, "
    "a verification code has been sent."
)


logger = logging.getLogger(__name__)


def _active_user_for_email(email):
    return User.objects.filter(
        email__iexact=email,
        is_active=True,
    ).first()


def _mask_email(email):
    local_part, separator, domain = email.partition("@")

    if not separator:
        return email

    visible = local_part[:1]
    return f"{visible}{'*' * max(3, len(local_part) - 1)}@{domain}"


def _clear_password_reset_authorization(request):
    request.session.pop("password_reset_verified", None)
    request.session.pop("password_reset_verified_email", None)
    request.session.modified = True


def forgot_password(request):
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            _clear_password_reset_authorization(request)

            clear_otp_session(request, PASSWORD_RESET_PURPOSE)
            user = _active_user_for_email(email)

            if not user:
                messages.success(
                    request,
                    PASSWORD_RESET_GENERIC_MESSAGE,
                )
                return redirect("forgot_password")

            otp = create_otp_session(
                request,
                PASSWORD_RESET_PURPOSE,
                email,
            )

            try:
                send_otp_email(
                    email,
                    otp,
                    PASSWORD_RESET_PURPOSE,
                )
            except Exception:
                logger.exception("Failed to send password reset OTP")
                clear_otp_session(request, PASSWORD_RESET_PURPOSE)
                messages.error(
                    request,
                    "We could not send the verification code right now. "
                    "Please try again in a moment.",
                )
                return redirect("forgot_password")

            messages.success(
                request,
                PASSWORD_RESET_GENERIC_MESSAGE,
            )
            return redirect("verify_reset_otp")
    else:
        form = ForgotPasswordForm()

    return render(
        request,
        "accounts/forgot_password.html",
        {"form": form},
    )


def verify_reset_otp(request):
    email = request.session.get("password_reset_email")

    if not email:
        messages.error(
            request,
            "Start a new password reset request to continue.",
        )
        return redirect("forgot_password")

    if request.method == "POST":
        form = OTPVerificationForm(request.POST)

        if form.is_valid():
            valid, error = verify_otp(
                request,
                PASSWORD_RESET_PURPOSE,
                form.cleaned_data["otp"],
            )

            if valid:
                user = _active_user_for_email(email)

                if not user:
                    clear_otp_session(
                        request,
                        PASSWORD_RESET_PURPOSE,
                    )
                    messages.error(
                        request,
                        "This password reset request is no longer valid.",
                    )
                    return redirect("forgot_password")

                clear_otp_session(
                    request,
                    PASSWORD_RESET_PURPOSE,
                )
                request.session["password_reset_verified"] = True
                request.session["password_reset_verified_email"] = email
                request.session.modified = True
                return redirect("reset_password")

            messages.error(request, error)
    else:
        form = OTPVerificationForm()

    return render(
        request,
        "accounts/verify_reset_otp.html",
        {
            "form": form,
            "masked_email": _mask_email(email),
            "resend_wait": get_resend_wait_seconds(
                request,
                PASSWORD_RESET_PURPOSE,
            ),
        },
    )


@require_POST
def resend_password_reset_otp(request):
    email = request.session.get("password_reset_email")

    if not email:
        messages.error(
            request,
            "Start a new password reset request to continue.",
        )
        return redirect("forgot_password")

    if not can_resend_otp(request, PASSWORD_RESET_PURPOSE):
        messages.warning(
            request,
            "Please wait before requesting another code.",
        )
        return redirect("verify_reset_otp")

    user = _active_user_for_email(email)

    if not user:
        clear_otp_session(request, PASSWORD_RESET_PURPOSE)
        messages.success(
            request,
            PASSWORD_RESET_GENERIC_MESSAGE,
        )
        return redirect("forgot_password")

    otp = create_otp_session(
        request,
        PASSWORD_RESET_PURPOSE,
        email,
    )

    try:
        send_otp_email(
            email,
            otp,
            PASSWORD_RESET_PURPOSE,
        )
    except Exception:
        logger.exception("Failed to send password reset OTP")
        clear_otp_session(request, PASSWORD_RESET_PURPOSE)
        messages.error(
            request,
            "We could not send the verification code right now. "
            "Please try again in a moment.",
        )
        return redirect("forgot_password")

    messages.success(
        request,
        PASSWORD_RESET_GENERIC_MESSAGE,
    )
    return redirect("verify_reset_otp")


def reset_password(request):
    verified = request.session.get("password_reset_verified") is True
    email = request.session.get("password_reset_verified_email")

    if not verified or not email:
        messages.error(
            request,
            "Verify a password reset code before choosing a new password.",
        )
        return redirect("forgot_password")

    user = _active_user_for_email(email)

    if not user:
        _clear_password_reset_authorization(request)
        clear_otp_session(request, PASSWORD_RESET_PURPOSE)
        messages.error(
            request,
            "This password reset request is no longer valid.",
        )
        return redirect("forgot_password")

    if request.method == "POST":
        form = GenVillaSetPasswordForm(user, request.POST)

        if form.is_valid():
            form.save()
            _clear_password_reset_authorization(request)
            clear_otp_session(request, PASSWORD_RESET_PURPOSE)
            messages.success(
                request,
                "Your password has been reset successfully.",
            )
            return redirect("login")
    else:
        form = GenVillaSetPasswordForm(user)

    return render(
        request,
        "accounts/reset_password.html",
        {"form": form},
    )


