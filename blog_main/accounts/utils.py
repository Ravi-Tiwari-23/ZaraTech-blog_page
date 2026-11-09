import math
import secrets
import resend

from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.template.loader import render_to_string
from django.utils import timezone


# ============================================================
# OTP CONFIGURATION
# ============================================================

# OTP is valid for 5 minutes.
OTP_EXPIRY_SECONDS = 300

# Maximum incorrect attempts before the OTP becomes invalid.
OTP_MAX_ATTEMPTS = 5

# User must wait 60 seconds before requesting another OTP.
OTP_RESEND_SECONDS = 60


# ============================================================
# OTP GENERATION
# ============================================================

def generate_otp():
    """
    Generate a cryptographically secure 6-digit OTP.
    """
    return f"{secrets.randbelow(1_000_000):06d}"


# ============================================================
# CREATE OTP SESSION
# ============================================================

def create_otp_session(request, purpose, email):
    """
    Generate an OTP and store only its hash in the Django session.

    The raw OTP is returned so it can be emailed to the user.
    It is never stored in the session.
    """

    otp = generate_otp()

    now = timezone.now().timestamp()

    request.session[f"{purpose}_otp_hash"] = make_password(otp)

    request.session[f"{purpose}_email"] = email

    request.session[f"{purpose}_expires_at"] = (
        now + OTP_EXPIRY_SECONDS
    )

    request.session[f"{purpose}_attempts"] = 0

    request.session[f"{purpose}_last_sent"] = now

    request.session.modified = True

    return otp


# ============================================================
# VERIFY OTP
# ============================================================

def verify_otp(request, purpose, submitted_otp):
    """
    Verify a submitted OTP.

    Returns:
        (True, None)
        when verification succeeds.

        (False, "error message")
        when verification fails.
    """

    otp_hash = request.session.get(
        f"{purpose}_otp_hash"
    )

    expires_at = request.session.get(
        f"{purpose}_expires_at"
    )

    attempts = request.session.get(
        f"{purpose}_attempts",
        0,
    )

    # No OTP currently exists.
    if not otp_hash or not expires_at:
        return (
            False,
            "No active verification code. Please request a new code.",
        )

    # OTP expired.
    if timezone.now().timestamp() > expires_at:
        clear_otp_session(request, purpose)

        return (
            False,
            "This verification code has expired. "
            "Please request a new code.",
        )

    # Too many incorrect attempts.
    if attempts >= OTP_MAX_ATTEMPTS:
        clear_otp_session(request, purpose)

        return (
            False,
            "Too many incorrect attempts. "
            "Please request a new code.",
        )

    # Incorrect OTP.
    if not check_password(
        submitted_otp,
        otp_hash,
    ):
        attempts += 1

        request.session[
            f"{purpose}_attempts"
        ] = attempts

        request.session.modified = True

        remaining = OTP_MAX_ATTEMPTS - attempts

        if remaining <= 0:
            clear_otp_session(request, purpose)

            return (
                False,
                "Too many incorrect attempts. "
                "Please request a new code.",
            )

        return (
            False,
            f"Incorrect verification code. "
            f"{remaining} attempt(s) remaining.",
        )

    # OTP is correct.
    return True, None



# RESEND COOLDOWN


def can_resend_otp(request, purpose):
    """
    Return True when the user is allowed to request another OTP.
    """

    return get_resend_wait_seconds(request, purpose) == 0


def get_resend_wait_seconds(request, purpose):
    """
    Return how many seconds remain before another OTP can be sent.
    """

    last_sent = request.session.get(
        f"{purpose}_last_sent"
    )

    if not last_sent:
        return 0

    elapsed = (
        timezone.now().timestamp()
        - last_sent
    )

    remaining = OTP_RESEND_SECONDS - elapsed

    return max(0, math.ceil(remaining))


# ============================================================
# CLEAR OTP SESSION
# ============================================================

def clear_otp_session(request, purpose):
    """
    Remove all OTP-related data for the specified purpose.
    """

    keys = [
        f"{purpose}_otp_hash",
        f"{purpose}_email",
        f"{purpose}_expires_at",
        f"{purpose}_attempts",
        f"{purpose}_last_sent",
    ]

    for key in keys:
        request.session.pop(key, None)

    request.session.modified = True


# ============================================================
# SEND OTP EMAIL
# ============================================================

def send_otp_email(email, otp, purpose):
    """
    Send OTP email using Resend HTTPS API.
    """

    if purpose == "email_verification":
        subject = f"{otp} is your ZaraTech verification code"
        heading = "Verify your email"
        intro = (
            "Use the verification code below to "
            "verify your ZaraTech account."
        )

    elif purpose == "password_reset":
        subject = f"{otp} is your ZaraTech password reset code"
        heading = "Reset your password"
        intro = (
            "Use the verification code below to "
            "continue resetting your ZaraTech password."
        )

    else:
        subject = f"{otp} is your ZaraTech verification code"
        heading = "Verification code"
        intro = (
            "Use the verification code below to continue."
        )

    context = {
        "otp": otp,
        "heading": heading,
        "intro": intro,
        "expiry_minutes": 5,
        "site_url": settings.SEO_BASE_URL,
    }

    html_body = render_to_string(
        "accounts/emails/otp_email.html",
        context,
    )

    resend.api_key = settings.RESEND_API_KEY

    response = resend.Emails.send(
        {
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [email],
            "subject": subject,
            "html": html_body,
        }
    )

    return response
