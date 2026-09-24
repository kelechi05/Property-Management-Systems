from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('maintenance', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='maintenancereport',
            name='title',
        ),
    ]
