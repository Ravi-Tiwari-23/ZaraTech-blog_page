from django.contrib import auth, messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group
from django.http import HttpResponseServerError
from django.shortcuts import redirect, render
from django.template.loader import get_template
from django.utils.http import url_has_allowed_host_and_scheme

from accounts.utils import (
    create_otp_session,
    send_otp_email,
)

from assignments.models import About
from blogs.models import Blog, Category, SavedPost

from .forms import RegistrationForm


def home(request):
    # ---------------------------------------------------------
    # FEATURED POSTS
    # ---------------------------------------------------------

    featured_post = list(
        Blog.objects.filter(
            is_featured=True,
            status="Published",
        ).prefetch_related(
            "author",
            "Category",
        ).order_by("-updated_at")[:4]
    )

    # If fewer than 4 posts are explicitly featured,
    # fill the remaining hero slides with popular/recent posts.
    if len(featured_post) < 4:
        featured_ids = [post.pk for post in featured_post]

        dynamic_featured = (
            Blog.objects.filter(
                status="Published",
            )
            .exclude(
                pk__in=featured_ids,
            )
            .order_by(
                "-views",
                "-updated_at",
            )
            .prefetch_related(
                "author",
                "Category",
            )[: 4 - len(featured_post)]
        )

        featured_post.extend(dynamic_featured)

    # ---------------------------------------------------------
    # LATEST POSTS
    # ---------------------------------------------------------

    posts = Blog.objects.filter(
        status="Published",
    ).prefetch_related(
        "author",
        "Category",
    ).order_by(
        "-created_at",
    )[:6]

    # ---------------------------------------------------------
    # POPULAR POSTS
    # ---------------------------------------------------------

    popular_posts = Blog.objects.filter(
        status="Published",
    ).prefetch_related(
        "author",
        "Category",
    ).order_by(
        "-views",
        "-created_at",
    )[:4]

    # ---------------------------------------------------------
    # ABOUT
    # ---------------------------------------------------------

    about = About.objects.order_by(
        "-updated_at",
        "-created_at",
    ).first()

    # ---------------------------------------------------------
    # CONTEXT
    # ---------------------------------------------------------

    context = {
        "featured_post": featured_post,
        "posts": posts,
        "popular_posts": popular_posts,
        "about": about,
        "saved_blog_ids": (
            set(
                SavedPost.objects.filter(
                    user=request.user,
                ).values_list("blog_id", flat=True)
            )
            if request.user.is_authenticated
            else set()
        ),
    }

    return render(
        request,
        "home.html",
        context,
    )


def register(request):
    # Logged-in users should not register again.
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            # -------------------------------------------------
            # CREATE USER AS INACTIVE
            # -------------------------------------------------

            user = form.save(commit=False)

            user.email = (
                form.cleaned_data["email"]
                .strip()
                .lower()
            )

            # User cannot log in before OTP verification.
            user.is_active = False

            user.save()

            # -------------------------------------------------
            # ASSIGN READER ROLE
            # -------------------------------------------------

            reader_group = Group.objects.filter(
                name="Reader"
            ).first()

            if reader_group:
                user.groups.add(reader_group)

            # -------------------------------------------------
            # CREATE OTP
            # -------------------------------------------------

            otp = create_otp_session(
                request,
                purpose="email_verification",
                email=user.email,
            )

            # -------------------------------------------------
            # SEND OTP EMAIL
            # -------------------------------------------------

            try:
                send_otp_email(
                    user.email,
                    otp,
                    purpose="email_verification",
                )

                messages.success(
                    request,
                    (
                        "We sent a 6-digit verification code "
                        "to your email address."
                    ),
                )

            except Exception:
                # Keep account inactive.
                # User can try the resend button on verification page.
                messages.error(
                    request,
                    (
                        "Your account was created, but we could not "
                        "send the verification email. "
                        "Please use Resend Code to try again."
                    ),
                )

            # -------------------------------------------------
            # REDIRECT TO VERIFY EMAIL PAGE
            # -------------------------------------------------

            return redirect("verify_email")

    else:
        form = RegistrationForm()

    context = {
        "form": form,
    }

    return render(
        request,
        "register.html",
        context,
    )


def login(request):
    if request.user.is_authenticated:
        if (
            request.user.is_superuser
            or request.user.groups.filter(
                name__in=("Manager", "Editor")
            ).exists()
        ):
            return redirect("dashboard")

        return redirect("home")

    if request.method == "POST":
        form = AuthenticationForm(
            request,
            request.POST,
        )

        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]

            user = auth.authenticate(
                request,
                username=username,
                password=password,
            )

            if user is not None:
                auth.login(
                    request,
                    user,
                )

                next_url = (
                    request.GET.get("next")
                    or request.POST.get("next")
                )

                if (
                    next_url
                    and url_has_allowed_host_and_scheme(
                        next_url,
                        allowed_hosts={
                            request.get_host()
                        },
                        require_https=request.is_secure(),
                    )
                ):
                    return redirect(next_url)

                if (
                    user.is_superuser
                    or user.groups.filter(
                        name__in=(
                            "Manager",
                            "Editor",
                        )
                    ).exists()
                ):
                    return redirect("dashboard")

                return redirect("home")

    else:
        form = AuthenticationForm()

    context = {
        "form": form,
    }

    return render(
        request,
        "login.html",
        context,
    )


def logout(request):
    auth.logout(request)

    return redirect("home")


def custom_404(request, exception):
    return render(
        request,
        "404.html",
        status=404,
    )


def custom_500(request):
    # Render without request context processors so the branded
    # fallback still works if the database itself is unavailable.
    content = get_template(
        "500.html"
    ).render(
        {
            "request": request,
        }
    )

    return HttpResponseServerError(
        content
    )
