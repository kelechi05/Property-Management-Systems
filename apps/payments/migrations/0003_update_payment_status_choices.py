from django.db import migrations, models


def migrate_payment_statuses(apps, schema_editor):
    Payment = apps.get_model('payments', 'Payment')

    Payment.objects.filter(status='paid').update(status='remitted')
    Payment.objects.filter(status__in=['pending', 'partial', 'overdue']).update(
        status='unremitted'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0002_sync_payment_property_names'),
    ]

    operations = [
        migrations.RunPython(migrate_payment_statuses, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='payment',
            name='status',
            field=models.CharField(
                choices=[('unremitted', 'Unremitted'), ('remitted', 'Remitted')],
                default='unremitted',
                max_length=20,
            ),
        ),
    ]
