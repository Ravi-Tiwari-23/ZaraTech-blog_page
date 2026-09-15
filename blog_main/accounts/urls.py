from django.urls import path

from . import views


urlpatterns = [
    path(
        "forgot-password/",
        views.forgot_password,
        name="forgot_password",
    ),
    path(
        "forgot-password/verify/",
        views.verify_reset_otp,
        name="verify_reset_otp",
    ),
    path(
        "forgot-password/resend/",
        views.resend_password_reset_otp,
        name="resend_password_reset_otp",
    ),
    path(
        "reset-password/",
        views.reset_password,
        name="reset_password",
    ),
    path(
        "verify-email/",
        views.verify_email,
        name="verify_email",
    ),
    path(
        "verify-email/resend/",
        views.resend_email_verification,
        name="resend_email_verification",
    ),
]
