from django.db import migrations


def create_installation(apps, schema_editor):
    apps.get_model("case_storage", "Installation").objects.get_or_create(pk=1)


class Migration(migrations.Migration):
    dependencies = [("case_storage", "0001_initial")]
    operations = [migrations.RunPython(create_installation, migrations.RunPython.noop)]
