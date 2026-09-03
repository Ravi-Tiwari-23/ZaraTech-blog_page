import sqlite3

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group, Permission

from blogs.models import Category, Blog, Comment
from assignments.models import About, SocialLink


class Command(BaseCommand):
    help = "Migrate existing GenVilla data from SQLite to MongoDB."

    def handle(self, *args, **options):
        sqlite_path = settings.BASE_DIR / "db.sqlite3"

        if not sqlite_path.exists():
            raise CommandError(f"SQLite database not found: {sqlite_path}")

        self.stdout.write(f"SQLite source: {sqlite_path}")
        self.stdout.write("Starting SQLite -> MongoDB migration...")

        # ---------------------------------------------------------
        # Safety check
        # ---------------------------------------------------------
        if (
            User.objects.exists()
            or Category.objects.exists()
            or Blog.objects.exists()
            or Comment.objects.exists()
            or About.objects.exists()
            or SocialLink.objects.exists()
        ):
            raise CommandError(
                "MongoDB already contains application data. "
                "Migration stopped to prevent duplicates."
            )

        connection = sqlite3.connect(sqlite_path)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        try:
            # =====================================================
            # 1. GROUPS
            # =====================================================
            self.stdout.write("Migrating groups...")

            cursor.execute("SELECT id, name FROM auth_group ORDER BY id")
            sqlite_groups = cursor.fetchall()

            group_map = {}

            for row in sqlite_groups:
                group, _ = Group.objects.get_or_create(name=row["name"])
                group_map[row["id"]] = group

            self.stdout.write(
                self.style.SUCCESS(
                    f"Groups migrated: {len(group_map)}"
                )
            )

            # =====================================================
            # 2. USERS
            # =====================================================
            self.stdout.write("Migrating users...")

            cursor.execute(
                """
                SELECT
                    id,
                    password,
                    last_login,
                    is_superuser,
                    username,
                    first_name,
                    last_name,
                    email,
                    is_staff,
                    is_active,
                    date_joined
                FROM auth_user
                ORDER BY id
                """
            )

            sqlite_users = cursor.fetchall()

            user_map = {}

            for row in sqlite_users:
                user = User.objects.create(
                    username=row["username"],
                    password=row["password"],  # preserve Django password hash
                    first_name=row["first_name"] or "",
                    last_name=row["last_name"] or "",
                    email=row["email"] or "",
                    is_staff=bool(row["is_staff"]),
                    is_active=bool(row["is_active"]),
                    is_superuser=bool(row["is_superuser"]),
                    last_login=row["last_login"],
                    date_joined=row["date_joined"],
                )

                user_map[row["id"]] = user

            self.stdout.write(
                self.style.SUCCESS(
                    f"Users migrated: {len(user_map)}"
                )
            )

            # =====================================================
            # 3. USER -> GROUP RELATIONSHIPS
            # =====================================================
            self.stdout.write("Migrating user/group relationships...")

            cursor.execute(
                """
                SELECT user_id, group_id
                FROM auth_user_groups
                """
            )

            user_group_rows = cursor.fetchall()

            memberships = 0

            for row in user_group_rows:
                user = user_map.get(row["user_id"])
                group = group_map.get(row["group_id"])

                if user and group:
                    user.groups.add(group)
                    memberships += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"User/group memberships migrated: {memberships}"
                )
            )

            # =====================================================
            # 4. DIRECT USER PERMISSIONS
            # =====================================================
            self.stdout.write("Migrating direct user permissions...")

            try:
                cursor.execute(
                    """
                    SELECT
                        up.user_id,
                        p.codename,
                        ct.app_label
                    FROM auth_user_user_permissions up
                    JOIN auth_permission p
                        ON p.id = up.permission_id
                    JOIN django_content_type ct
                        ON ct.id = p.content_type_id
                    """
                )

                permission_rows = cursor.fetchall()

                migrated_permissions = 0

                for row in permission_rows:
                    user = user_map.get(row["user_id"])

                    if not user:
                        continue

                    permission = Permission.objects.filter(
                        codename=row["codename"],
                        content_type__app_label=row["app_label"],
                    ).first()

                    if permission:
                        user.user_permissions.add(permission)
                        migrated_permissions += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Direct user permissions migrated: "
                        f"{migrated_permissions}"
                    )
                )

            except sqlite3.OperationalError:
                self.stdout.write(
                    self.style.WARNING(
                        "No direct user permissions found."
                    )
                )

            # =====================================================
            # 5. CATEGORIES
            # =====================================================
            self.stdout.write("Migrating categories...")

            cursor.execute(
                """
                SELECT
                    id,
                    category_name,
                    created_at,
                    updated_at
                FROM blogs_category
                ORDER BY id
                """
            )

            sqlite_categories = cursor.fetchall()

            category_map = {}

            for row in sqlite_categories:
                category = Category.objects.create(
                    category_name=row["category_name"]
                )

                Category.objects.filter(pk=category.pk).update(
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )

                category.refresh_from_db()
                category_map[row["id"]] = category

            self.stdout.write(
                self.style.SUCCESS(
                    f"Categories migrated: {len(category_map)}"
                )
            )

            # =====================================================
            # 6. BLOG POSTS
            # =====================================================
            self.stdout.write("Migrating blog posts...")

            cursor.execute(
                """
                SELECT
                    id,
                    title,
                    slug,
                    Category_id,
                    author_id,
                    featured_image,
                    short_description,
                    blog_body,
                    status,
                    is_featured,
                    views,
                    created_at,
                    updated_at
                FROM blogs_blog
                ORDER BY id
                """
            )

            sqlite_blogs = cursor.fetchall()

            blog_map = {}

            for row in sqlite_blogs:
                author = user_map.get(row["author_id"])
                category = category_map.get(row["Category_id"])

                if author is None:
                    raise CommandError(
                        f"Author {row['author_id']} missing "
                        f"for blog {row['id']}."
                    )

                if category is None:
                    raise CommandError(
                        f"Category {row['Category_id']} missing "
                        f"for blog {row['id']}."
                    )

                blog = Blog.objects.create(
                    title=row["title"],
                    slug=row["slug"],
                    Category=category,
                    author=author,
                    featured_image=row["featured_image"],
                    short_description=row["short_description"],
                    blog_body=row["blog_body"],
                    status=row["status"],
                    is_featured=bool(row["is_featured"]),
                    views=row["views"] or 0,
                )

                Blog.objects.filter(pk=blog.pk).update(
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )

                blog.refresh_from_db()
                blog_map[row["id"]] = blog

            self.stdout.write(
                self.style.SUCCESS(
                    f"Blogs migrated: {len(blog_map)}"
                )
            )

            # =====================================================
            # 7. COMMENTS
            # =====================================================
            self.stdout.write("Migrating comments...")

            cursor.execute(
                """
                SELECT
                    id,
                    blog_id,
                    user_id,
                    body,
                    is_approved,
                    created_at,
                    updated_at
                FROM blogs_comment
                ORDER BY id
                """
            )

            sqlite_comments = cursor.fetchall()

            comment_count = 0

            for row in sqlite_comments:
                blog = blog_map.get(row["blog_id"])
                user = user_map.get(row["user_id"])

                if blog is None:
                    raise CommandError(
                        f"Blog {row['blog_id']} missing "
                        f"for comment {row['id']}."
                    )

                if user is None:
                    raise CommandError(
                        f"User {row['user_id']} missing "
                        f"for comment {row['id']}."
                    )

                comment = Comment.objects.create(
                    blog=blog,
                    user=user,
                    body=row["body"],
                    is_approved=bool(row["is_approved"]),
                )

                Comment.objects.filter(pk=comment.pk).update(
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )

                comment_count += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"Comments migrated: {comment_count}"
                )
            )

            # =====================================================
            # 8. ABOUT
            # =====================================================
            self.stdout.write("Migrating About records...")

            cursor.execute(
                """
                SELECT
                    id,
                    about_heading,
                    about_description,
                    created_at,
                    updated_at
                FROM assignments_about
                ORDER BY id
                """
            )

            sqlite_about = cursor.fetchall()

            for row in sqlite_about:
                about = About.objects.create(
                    about_heading=row["about_heading"],
                    about_description=row["about_description"],
                )

                About.objects.filter(pk=about.pk).update(
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"About records migrated: {len(sqlite_about)}"
                )
            )

            # =====================================================
            # 9. SOCIAL LINKS
            # =====================================================
            self.stdout.write("Migrating social links...")

            cursor.execute(
                """
                SELECT
                    id,
                    platform,
                    link,
                    created_at,
                    updated_at
                FROM assignments_sociallink
                ORDER BY id
                """
            )

            sqlite_social = cursor.fetchall()

            for row in sqlite_social:
                social = SocialLink.objects.create(
                    platform=row["platform"],
                    link=row["link"],
                )

                SocialLink.objects.filter(pk=social.pk).update(
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Social links migrated: {len(sqlite_social)}"
                )
            )

            # =====================================================
            # FINAL SUMMARY
            # =====================================================
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    "SQLite -> MongoDB migration completed successfully."
                )
            )

            self.stdout.write("")
            self.stdout.write("MongoDB record counts:")
            self.stdout.write(f"Users:       {User.objects.count()}")
            self.stdout.write(f"Groups:      {Group.objects.count()}")
            self.stdout.write(f"Categories:  {Category.objects.count()}")
            self.stdout.write(f"Blogs:       {Blog.objects.count()}")
            self.stdout.write(f"Comments:    {Comment.objects.count()}")
            self.stdout.write(f"About:       {About.objects.count()}")
            self.stdout.write(f"SocialLinks: {SocialLink.objects.count()}")

        finally:
            connection.close()