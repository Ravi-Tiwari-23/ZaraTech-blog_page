# GenVilla Insights

GenVilla Insights is the Django application behind
[blog.genvilla.in](https://blog.genvilla.in). It provides the public editorial
site, authentication, comments, saved posts, and the role-based content
dashboard used by managers and editors.

## Stack

- Python 3.12 and Django 5.2
- MongoDB through `django-mongodb-backend`
- Cloudinary for uploaded media
- WhiteNoise for versioned static assets
- Gunicorn in an ARM64 container
- Amazon ECS Fargate, ECR, ALB, CloudWatch Logs, and Secrets Manager
- AWS CDK in TypeScript
- GitHub Actions with AWS OIDC

Production deliberately keeps the existing MongoDB database and Cloudinary
media. Deploying the application does not copy or replace that data.

## Repository layout

```text
.
├── .github/workflows/       # CI and prod deployment workflows
├── blog_main/               # Django project and applications
│   ├── manage.py
│   ├── accounts/
│   ├── assignments/
│   ├── blog_main/
│   ├── blogs/
│   ├── dashboards/
│   └── templates/
├── infra/                   # AWS CDK application
├── Dockerfile
└── requirements.txt
```

## Local development

Create and activate a virtual environment from the repository root, then
install the pinned dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Copy `.env.example` to `blog_main/.env` and supply development credentials.
That path matches `BASE_DIR / ".env"` in the Django settings. Never commit the
completed `.env` file. The MongoDB-backed application is started with:

```bash
cd blog_main
DJANGO_SETTINGS_MODULE=blog_main.settings_mongo python manage.py migrate
DJANGO_SETTINGS_MODULE=blog_main.settings_mongo python manage.py runserver
```

Open <http://127.0.0.1:8000/>. The dashboard is at `/dashboard/`, Django Admin
is at `/admin/`, and the service health endpoint is `/healthz/`.

The read-only published-posts endpoint is `GET /api/posts/`. It requires the
same secret on the blog server and its server-side consumer in the
`X-API-Key` header. Generate a secret locally without saving its output to a
tracked file:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Add `GENVILLA_BLOG_API_KEY=<secret>` manually to the ignored local `.env` when
needed. For a Render deployment, add the same variable manually under
`genvilla-blog` -> **Environment**. Never expose this value to browser code or
commit it to the repository. Restart `runserver` after adding or changing the
value because Django settings are loaded when the server process starts; an
already-running process does not reload settings when `.env` changes.

## Validation

Run the same application checks used by CI:

```bash
cd blog_main
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py collectstatic --noinput
python manage.py test
```

Validate the infrastructure from the repository root:

```bash
npm ci --prefix infra
npm run check --prefix infra
npm run format --prefix infra
npm run synth --prefix infra -- --context genvilla-blog:imageTag=ci
```

Build the production container locally with:

```bash
docker build --platform linux/arm64 -t genvilla-blog:local .
```

## CI/CD

`.github/workflows/ci.yml` runs Django checks, migration drift detection, the
test suite, CDK validation, and an ARM64 container build for pushes and pull
requests targeting `main` or `prod`.

`.github/workflows/deploy-prod.yml` is the only production deployment path. A
push to `prod`:

1. reruns application checks and tests;
2. builds an immutable image tagged with the Git commit SHA;
3. pushes the image to `genvilla-blog` in ECR;
4. reviews and deploys the `GenvillaBlogProd` CDK diff; and
5. smoke-tests the public HTTPS health endpoint and homepage through Cloudflare.

The shared load balancer accepts traffic only from Cloudflare. Smoke tests
therefore use the public hostname, with bounded connection timeouts and retries.
The health response must identify the `genvilla-blog` service and report `ok`.

The workflow uses the branch-restricted GitHub `production` environment and
short-lived AWS credentials through OIDC. No AWS access keys or application
secrets are stored in GitHub.

## Production infrastructure

Production runs in AWS account `013565030464`, region `ap-south-1`, on the
shared `genvilla-prod` ECS cluster and application load balancer.

- `GenvillaBlogFoundation` owns the ECR repository, runtime secret, GitHub OIDC
  deployment role, retained CloudWatch log group, and media/CDN resources.
- `GenvillaBlogProd` owns the ECS task definition and service, CloudWatch log
  permissions, autoscaling policy, target group, TLS certificate attachment,
  and the `blog.genvilla.in` listener rule.

The ECS task loads `MONGODB_URI`, `MONGODB_NAME`, Django, Cloudinary, and email
credentials from the `genvilla-blog/runtime` secret. The migration container
must finish successfully before Gunicorn starts. ECS deployment circuit
breaking and CloudFormation rollback protect the current healthy revision.

The ALB and container readiness probes call `GET /healthz/`. That exact path is
answered before Django validates the probe's private-IP `Host` header; all
normal application requests continue through strict `ALLOWED_HOSTS` checking.

Useful operational commands:

```bash
aws ecs describe-services \
  --cluster genvilla-prod \
  --services genvilla-blog-prod \
  --region ap-south-1

aws logs tail /ecs/genvilla-prod/blog \
  --follow \
  --region ap-south-1
```

Routine releases should be made by pushing a reviewed commit to `prod`; do not
run an ad-hoc ECS image update. Foundation changes are exceptional and should
be reviewed with `cdk diff` before `npm run deploy:foundation --prefix infra`.

## Runtime configuration

The required variable names are documented in `.env.example`. Production
values belong in AWS Secrets Manager. If a credential is rotated, update the
secret and deploy a new task revision so ECS injects the new value.
