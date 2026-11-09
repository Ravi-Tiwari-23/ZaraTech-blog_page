# ZaraTech Insights

ZaraTech Insights is a Django technology publication covering artificial
intelligence, cloud engineering, cybersecurity, web development, data and
developer experience. It includes the existing authentication, OTP, comments,
saved posts, editorial dashboard, Cloudinary media and read-only posts API.

## Architecture

- Python 3.12 and Django 5.2
- MongoDB through `django-mongodb-backend`
- Cloudinary for uploaded media
- WhiteNoise and Vercel CDN for static assets
- Resend for transactional email
- Vercel Python runtime for hosting

The deployment reuses the existing service credentials but uses the isolated
MongoDB database name `zaratech_blog`. Never point the ZaraTech content seeder
at the original `genvilla_db` database.

## Local setup

Create a virtual environment, install dependencies and copy `.env.example` to
`blog_main/.env`. Supply credentials only in that ignored file.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate --settings=blog_main.settings_mongo
python manage.py seed_zaratech_blog --settings=blog_main.settings_mongo
python manage.py runserver --settings=blog_main.settings_mongo
```

`seed_zaratech_blog` deletes and replaces blog/category content only when
`MONGODB_NAME` is exactly `zaratech_blog`; it refuses to run against any other
database.

## Validation

```powershell
python manage.py check --settings=blog_main.settings_mongo
python manage.py collectstatic --noinput --settings=blog_main.settings
python manage.py test blog_main.tests blogs.tests accounts.tests dashboards.tests assignments.tests --settings=blog_main.settings
```

## Deployment

Vercel automatically detects Django from the root `manage.py`, installs
`requirements.txt`, runs `collectstatic`, and serves the application through
the outer `blog_main/wsgi.py` bridge.

The production project is `zaratech-blog`. Configure the variables documented
in `.env.example` in Vercel for Production and Preview. Secret values must
remain in Vercel's encrypted environment store and must never be committed.

Deploy with:

```powershell
npx vercel@latest deploy --prod --yes
```

Production URL: <https://zaratech-blog.vercel.app>

The API remains `GET /api/posts/` and requires the existing
`GENVILLA_BLOG_API_KEY` value through the `X-API-Key` request header.
