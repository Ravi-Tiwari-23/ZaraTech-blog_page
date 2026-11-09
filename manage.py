#!/usr/bin/env python
import os
import sys
from pathlib import Path


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent
    sys.path.insert(0, str(project_root / "blog_main"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blog_main.settings_mongo")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
