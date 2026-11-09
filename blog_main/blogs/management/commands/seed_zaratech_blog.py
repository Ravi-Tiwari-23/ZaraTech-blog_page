from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from blogs.models import Blog, Category


POSTS = (
    {
        "category": "Artificial Intelligence",
        "title": "How AI Agents Are Changing the Way Software Gets Built",
        "short_description": (
            "A practical look at agentic workflows, their limits, and the engineering "
            "patterns teams need before putting autonomous tools into production."
        ),
        "body": """## From assistants to workflows

AI coding tools are moving beyond single prompts. Modern agents can inspect a repository, plan a change, run tools, evaluate results and revise their work. That loop is useful, but it does not remove the need for engineering discipline.

## The architecture that matters

Reliable agents need constrained tools, explicit permissions, observable actions and deterministic checks. Treat every tool call like an API integration: validate inputs, limit scope and retain an audit trail.

## Where teams get value today

- Repetitive maintenance and dependency updates
- Test generation and failure investigation
- Repository navigation and documentation
- Small, well-specified implementation tasks

The best results come from combining clear acceptance criteria with fast automated feedback. Agents amplify a strong development system; they do not replace one.
""",
    },
    {
        "category": "Cloud Engineering",
        "title": "Serverless Django in Production: What Changes and What Does Not",
        "short_description": (
            "Understand cold starts, connection management, static assets and background "
            "work before moving a traditional Django application to serverless hosting."
        ),
        "body": """## Django still behaves like Django

The request lifecycle, middleware stack, ORM and URL routing stay familiar on a serverless platform. The difference is the runtime: instances are ephemeral, scale independently and may disappear between requests.

## Design for an ephemeral filesystem

User uploads belong in object storage such as Cloudinary or S3. Static assets should be collected during the build and served through a CDN or an application layer designed for immutable files.

## Watch database connections

Every serverless instance can create connections. Use a managed database, sensible timeouts and a driver suited to bursty workloads. Keep slow setup work out of module import paths.

## Move background jobs elsewhere

Email delivery, media processing and long-running jobs should use a queue or managed workflow. A request handler should complete quickly and remain safe to retry.
""",
    },
    {
        "category": "Cybersecurity",
        "title": "API Keys Done Right: A Small Security Checklist That Prevents Big Problems",
        "short_description": (
            "A concise guide to storing, comparing, rotating and monitoring server-to-server "
            "API keys without accidentally exposing them to browsers or logs."
        ),
        "body": """## Keep keys on the server

An API key embedded in browser JavaScript is public. Server-to-server keys belong in environment variables or a managed secret store and should only be attached by trusted backend code.

## Fail closed

Missing configuration must never turn authentication off. If the expected server key is absent, return a generic configuration failure and do not compare two empty values.

## Compare safely

Use a constant-time comparison function. Return the same generic unauthorized response for missing and incorrect client keys so callers cannot learn anything about the expected value.

## Rotate and observe

Rotate exposed keys immediately, avoid logging headers, and monitor unusual request volume. A key is one control—not a replacement for TLS, rate limiting and least privilege.
""",
    },
    {
        "category": "Web Development",
        "title": "The Modern Web Stack Is a Set of Trade-offs, Not a Shopping List",
        "short_description": (
            "Choose frameworks, databases and hosting based on operational needs instead of "
            "copying a fashionable stack that solves someone else's problem."
        ),
        "body": """## Start with the product shape

A content site, real-time collaboration tool and internal dashboard have different constraints. Write down traffic patterns, latency goals, data relationships and the team's operational experience before choosing technology.

## Prefer boring boundaries

Clear HTTP interfaces, portable data models and conventional authentication age better than tightly coupled platform features. Managed services are valuable when their operational benefit exceeds the switching cost.

## Optimize for change

The best stack is one your team can understand, test and deploy confidently. Measure real bottlenecks before adding caches, queues or distributed components.

Technology choices are reversible when boundaries are deliberate. Keep the core simple and earn complexity with evidence.
""",
    },
    {
        "category": "Data Engineering",
        "title": "From Raw Events to Reliable Analytics: Building a Data Pipeline You Can Trust",
        "short_description": (
            "Learn the foundations of dependable analytics pipelines: contracts, idempotency, "
            "quality checks, lineage and recovery from partial failures."
        ),
        "body": """## Define the contract first

Every event needs an owner, schema and clear meaning. Version contracts deliberately and keep producers from silently changing fields that downstream models depend on.

## Make processing repeatable

Idempotent jobs can safely retry without duplicating results. Store checkpoints, use stable event identifiers and separate raw immutable data from cleaned analytical models.

## Test the data, not just the code

Validate freshness, volume, uniqueness and accepted ranges. Alert on violations before dashboards quietly become misleading.

## Design recovery paths

Document how to replay a window, backfill a new field and isolate malformed records. Reliable pipelines are defined as much by recovery as by the happy path.
""",
    },
    {
        "category": "Developer Experience",
        "title": "Developer Experience Is Infrastructure: Five Improvements That Compound",
        "short_description": (
            "Fast setup, useful errors, dependable tests, preview environments and clear ownership "
            "give engineering teams more leverage than another productivity dashboard."
        ),
        "body": """## Reduce time to first change

A new contributor should be able to clone the repository, configure safe local defaults and run tests from documented commands. Every undocumented setup step becomes recurring support work.

## Make feedback fast

Keep a focused test loop under a minute, show actionable errors and run expensive validation in parallel. Developers should learn about mistakes while the relevant context is still fresh.

## Give every change a place to live

Preview environments make review concrete. Pair them with seeded, non-sensitive data and automated cleanup.

## Treat documentation as code

Keep operational instructions beside the implementation, review them with changes and test critical examples. Good developer experience is a maintained system, not a one-time initiative.
""",
    },
)


class Command(BaseCommand):
    help = "Replace content in the isolated zaratech_blog database with technology posts."

    def handle(self, *args, **options):
        database_name = settings.DATABASES["default"].get("NAME")
        if database_name != "zaratech_blog":
            raise CommandError(
                "Refusing to seed: MONGODB_NAME must be exactly 'zaratech_blog'."
            )

        Blog.objects.all().delete()
        Category.objects.all().delete()

        author, _ = User.objects.get_or_create(
            username="zaratech-editor",
            defaults={
                "first_name": "ZaraTech",
                "last_name": "Editorial",
                "is_active": False,
            },
        )
        if author.has_usable_password():
            author.set_unusable_password()
            author.save(update_fields=["password"])

        categories = {}
        now = timezone.now()
        for index, item in enumerate(POSTS):
            category = categories.get(item["category"])
            if category is None:
                category = Category.objects.create(
                    category_name=item["category"]
                )
                categories[item["category"]] = category
            post = Blog.objects.create(
                title=item["title"],
                Category=category,
                author=author,
                short_description=item["short_description"],
                blog_body=item["body"],
                status="Published",
                is_featured=index < 4,
                meta_description=item["short_description"][:160],
                focus_keyword=item["category"],
            )
            Blog.objects.filter(pk=post.pk).update(
                created_at=now - timedelta(days=index * 3),
            )

        self.stdout.write(
            self.style.SUCCESS(f"Created {len(POSTS)} ZaraTech technology posts.")
        )
