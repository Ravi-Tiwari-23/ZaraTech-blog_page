from urllib.parse import urljoin, urlsplit

from django.conf import settings

from .models import Category
from assignments.models import SocialLink


PRIVATE_PATH_PREFIXES = (
    '/account/',
    '/admin/',
    '/blogs/search/',
    '/dashboard/',
    '/login/',
    '/logout/',
    '/register/',
    '/saved/',
)


def absolute_public_url(path):
    if not path:
        return ''
    parsed = urlsplit(path)
    if parsed.scheme and parsed.netloc:
        return path
    return urljoin(f'{settings.SEO_BASE_URL}/', path.lstrip('/'))


def get_seo_defaults(request):
    canonical_url = absolute_public_url(request.path)
    return {
        'canonical_url': canonical_url,
        'default_social_image_url': absolute_public_url(
            f"{settings.STATIC_URL.rstrip('/')}/images/og.png"
        ),
        'seo_noindex': request.path.startswith(PRIVATE_PATH_PREFIXES),
        'site_url': settings.SEO_BASE_URL,
    }

def get_categories(request):
    categories = Category.objects.all()
    return dict(categories=categories)


def get_social_links(request):
    social_links = SocialLink.objects.all()
    return dict(social_links=social_links)


def get_user_roles(request):
    user = request.user
    if not user.is_authenticated:
        return {'is_manager': False, 'is_editor': False, 'has_dashboard_access': False}
    is_manager = user.is_superuser or user.groups.filter(name='Manager').exists()
    is_editor = user.groups.filter(name='Editor').exists()
    return {
        'is_manager': is_manager,
        'is_editor': is_editor,
        'has_dashboard_access': is_manager or is_editor,
    }
