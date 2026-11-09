import os
import sys
from pathlib import Path


DJANGO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(DJANGO_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blog_main.settings_mongo")

from django.core.wsgi import get_wsgi_application  # noqa: E402


application = get_wsgi_application()
