from django.db import migrations


def sync_payment_property_names(apps, schema_editor):
    Payment = apps.get_model('payments', 'Payment')

    for payment in Payment.objects.select_related('property').exclude(property__isnull=True):
        property_name = payment.property.property_name
        if payment.property_name != property_name:
            payment.property_name = property_name
            payment.save(update_fields=['property_name'])


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(sync_payment_property_names, migrations.RunPython.noop),
    ]
