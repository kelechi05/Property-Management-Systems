from django.conf import settings
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import models
from django.utils.text import Truncator

from apps.properties.models import Landlord, Property
from apps.tenants.models import Tenant


class MaintenanceReport(models.Model):
    STATUS_NEW = 'new'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_RESOLVED = 'resolved'
    STATUS_CLOSED = 'closed'

    STATUS_CHOICES = [
        (STATUS_NEW, 'New'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_RESOLVED, 'Resolved'),
        (STATUS_CLOSED, 'Closed'),
    ]

    PRIORITY_LOW = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH = 'high'
    PRIORITY_URGENT = 'urgent'

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_HIGH, 'High'),
        (PRIORITY_URGENT, 'Urgent'),
    ]

    SUBMITTED_BY_STAFF = 'staff'
    SUBMITTED_BY_TENANT = 'tenant'

    SUBMITTED_BY_CHOICES = [
        (SUBMITTED_BY_STAFF, 'Staff'),
        (SUBMITTED_BY_TENANT, 'Tenant'),
    ]

    landlord = models.ForeignKey(
        Landlord,
        on_delete=models.CASCADE,
        related_name='maintenance_reports',
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.SET_NULL,
        related_name='maintenance_reports',
        null=True,
        blank=True,
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.SET_NULL,
        related_name='maintenance_reports',
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='submitted_maintenance_reports',
        null=True,
        blank=True,
    )
    assigned_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='assigned_maintenance_reports',
        null=True,
        blank=True,
    )
    submitted_by = models.CharField(
        max_length=20,
        choices=SUBMITTED_BY_CHOICES,
    )
    description = models.TextField()
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_MEDIUM,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
    )
    cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Cost of the maintenance work.',
    )
    staff_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        errors = {}

        if not self.landlord_id and self.property_id:
            self.landlord = self.property.landlord

        if not self.landlord_id and self.tenant_id and self.tenant.landlord_id:
            self.landlord = self.tenant.landlord

        if not self.landlord_id:
            errors[NON_FIELD_ERRORS] = 'A landlord is required for every maintenance report.'

        if self.property_id and self.landlord_id and self.property.landlord_id != self.landlord_id:
            errors['property'] = 'The selected property must belong to the selected landlord.'

        if self.tenant_id and self.landlord_id and self.tenant.landlord_id != self.landlord_id:
            errors['tenant'] = 'The selected tenant must belong to the selected landlord.'

        if self.cost is not None and self.cost < 0:
            errors['cost'] = 'Cost cannot be negative.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.property_id and not self.landlord_id:
            self.landlord = self.property.landlord
        if self.tenant_id and not self.landlord_id and self.tenant.landlord_id:
            self.landlord = self.tenant.landlord
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.display_label()} - {self.get_status_display()}'

    def display_label(self):
        return Truncator(self.description).chars(60)
