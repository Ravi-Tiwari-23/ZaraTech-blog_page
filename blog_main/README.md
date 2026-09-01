# GenVilla Insights

GenVilla Insights is a Django real-estate editorial blog with an image-led homepage, dynamic featured stories, popular-post rankings, categories, search, comments, authentication, and a role-based content dashboard.

## Main features

- Responsive property-portal-inspired blog design
- Automatically rotating featured-story slider
- Dynamic featured images loaded from each blog post
- “Popular on GenVilla” sections ranked by article views
- Category browsing and full-text blog search
- Article reading time and session-based view counting
- Saved-article bookmarks stored in the browser
- Comments for authenticated readers
- Manager and Editor dashboard roles
- Django Admin access

## Run in VS Code

Open this folder in Visual Studio Code:

```text
D:\genvilla_blog\blog\blog_main
```

The included VS Code configuration already selects the project virtual environment.

1. Open **Run and Debug** with `Ctrl+Shift+D`.
2. Select **Run GenVilla Django**.
3. Press `F5`.
4. Open <http://127.0.0.1:8000/>.

Press `Shift+F5` to stop the server.

## Run from the VS Code terminal

From this directory, run:

```powershell
..\venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py runserver
```

If PowerShell activation is unavailable, run the interpreter directly:

```powershell
..\venv\Scripts\python.exe manage.py migrate
..\venv\Scripts\python.exe manage.py runserver
```

## Site URLs

| Page | URL |
| --- | --- |
| Public blog | <http://127.0.0.1:8000/> |
| Editorial dashboard | <http://127.0.0.1:8000/dashboard/> |
| Django Admin | <http://127.0.0.1:8000/admin/> |
| Dashboard admin shortcut | <http://127.0.0.1:8000/dashboard/admin> |
| Login | <http://127.0.0.1:8000/login/> |
| Registration | <http://127.0.0.1:8000/register/> |

## Content behavior

### Featured stories

Posts marked as featured are shown first. If fewer than four featured posts exist, the homepage supplements them with published posts ordered by views and update time. When at least two stories are available, the hero automatically changes every six seconds and can also be controlled manually.

### Popular posts

“Popular on GenVilla” is generated dynamically from published posts ordered by highest view count. Each card uses that post’s own uploaded `featured_image`. The current article is excluded from the popular list on its detail page.

### User roles

- **Manager:** manages categories, users, and all posts.
- **Editor:** manages their own posts and accesses editorial statistics.
- **Reader:** browses posts and can comment after logging in.

## Project structure

```text
blog_main/
├── .vscode/          # VS Code interpreter and run configuration
├── assignments/      # About and social-link content
├── blog_main/        # Django settings, URLs, views, and static files
├── blogs/            # Blog, category, comment models, forms, and views
├── dashboards/       # Editorial dashboard and role management
├── media/            # Uploaded featured images
├── templates/        # Public and dashboard templates
├── db.sqlite3        # Local development database
└── manage.py         # Django command entry point
```

The virtual environment and pinned requirements are located one directory above this folder.

## Useful commands

```powershell
# Validate the Django configuration
..\venv\Scripts\python.exe manage.py check

# Apply database migrations
..\venv\Scripts\python.exe manage.py migrate

# Create an administrator account
..\venv\Scripts\python.exe manage.py createsuperuser

# Run automated tests
..\venv\Scripts\python.exe manage.py test
```

## Technology

- Python 3.12
- Django 4.2
- SQLite
- Django Crispy Forms with Bootstrap 4
- HTML, CSS, and vanilla JavaScript
- Pillow for uploaded images

This configuration is intended for local development. Review Django security and deployment settings before using it in production.
