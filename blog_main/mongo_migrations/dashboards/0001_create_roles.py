from django.db import migrations


def create_dashboard_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="Manager")
    Group.objects.get_or_create(name="Editor")


def remove_dashboard_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=("Manager", "Editor")).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            create_dashboard_roles,
            remove_dashboard_roles,
        ),
    ]