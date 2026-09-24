from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('properties', '0008_landlord_commission_percentage'),
        ('tenants', '0002_tenant_tenancy_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='MaintenanceReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('submitted_by', models.CharField(choices=[('staff', 'Staff'), ('tenant', 'Tenant')], max_length=20)),
                ('title', models.CharField(max_length=180)),
                ('description', models.TextField()),
                ('priority', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('urgent', 'Urgent')], default='medium', max_length=20)),
                ('status', models.CharField(choices=[('new', 'New'), ('in_progress', 'In Progress'), ('resolved', 'Resolved'), ('closed', 'Closed')], default='new', max_length=20)),
                ('cost', models.DecimalField(blank=True, decimal_places=2, help_text='Cost of the maintenance work.', max_digits=12, null=True)),
                ('staff_note', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('assigned_staff', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_maintenance_reports', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='submitted_maintenance_reports', to=settings.AUTH_USER_MODEL)),
                ('landlord', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='maintenance_reports', to='properties.landlord')),
                ('property', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='maintenance_reports', to='properties.property')),
                ('tenant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='maintenance_reports', to='tenants.tenant')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
