# Django Blog

A Django blog application with posts, categories, comments, search, user authentication, and a role-based dashboard for managing content and users.

## Project location

The updated project is located at:

```text
D:\ravi2\Desktop\blog
```

Open this folder in VS Code. Do not use the older copy at `C:\Users\ravi2\Desktop\blog` if you want to run the latest changes.

## Project structure

```text
blog/
├── requirements.txt
├── README.md
└── blog_main/
    ├── manage.py
    ├── blog_main/       # Django settings, main URLs, views, and static files
    ├── blogs/           # Posts, categories, comments, and public blog pages
    ├── dashboards/      # Dashboard, post management, and user management
    ├── assignments/     # Additional site content and models
    └── templates/       # Public and dashboard HTML templates
```

## Setup in VS Code on Windows

1. In VS Code, select **File > Open Folder**.
2. Open `D:\ravi2\Desktop\blog`.
3. Open a new terminal.
4. Run the following commands from the project root:

```bat
venv\Scripts\activate.bat
python -m pip install -r requirements.txt
cd blog_main
python manage.py migrate
python manage.py runserver
```

Open <http://127.0.0.1:8000/> after the server starts.

Stop the development server by pressing `Ctrl+C` in the terminal.

## VS Code Python interpreter

If VS Code asks you to choose an interpreter:

1. Press `Ctrl+Shift+P`.
2. Select **Python: Select Interpreter**.
3. Choose:

```text
D:\ravi2\Desktop\blog\venv\Scripts\python.exe
```

## Running from the application directory

If the terminal is already in `D:\ravi2\Desktop\blog\blog_main`, install the dependencies using the requirements file one directory above:

```bat
python -m pip install -r ..\requirements.txt
python manage.py migrate
python manage.py runserver
```

## Common errors

### Python cannot find `manage.py`

The terminal is in the wrong directory. Move to the directory containing `manage.py`:

```bat
cd /d D:\ravi2\Desktop\blog\blog_main
python manage.py runserver
```

Do not run `cd dir`. That command tries to enter a folder literally named `dir`.

### `No module named 'django'`

Activate the virtual environment and install the project dependencies:

```bat
cd /d D:\ravi2\Desktop\blog
venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```

If necessary, update pip first:

```bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### The terminal displays `>>>`

This is the interactive Python prompt, not the Django server. Exit it with:

```python
exit()
```

Then run `python manage.py runserver` from the directory containing `manage.py`.

## Useful Django commands

```bat
# Check the project configuration
python manage.py check

# Create migrations after changing models
python manage.py makemigrations

# Apply database migrations
python manage.py migrate

# Create an administrator account
python manage.py createsuperuser

# Run the tests
python manage.py test
```

## Main dependencies

- Django 4.2
- django-crispy-forms
- crispy-bootstrap4
- Pillow

The complete pinned dependency list is in `requirements.txt`.
