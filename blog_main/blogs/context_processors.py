from .models import Category
from assignments.models import SocialLink

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
