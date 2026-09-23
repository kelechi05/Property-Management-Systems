from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.properties.models import Property
from apps.tenants.models import Tenant


class Payment(models.Model):
    STATUS_UNREMITTED = 'unremitted'
    STATUS_REMITTED = 'remitted'

    STATUS_CHOICES = [
        (STATUS_UNREMITTED, 'Unremitted'),
        (STATUS_REMITTED, 'Remitted'),
    ]

    PAYMENT_METHOD_CASH = 'cash'
    PAYMENT_METHOD_TRANSFER = 'transfer'
    PAYMENT_METHOD_CARD = 'card'
    PAYMENT_METHOD_OTHER = 'other'

    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_METHOD_CASH, 'Cash'),
        (PAYMENT_METHOD_TRANSFER, 'Transfer'),
        (PAYMENT_METHOD_CARD, 'Card'),
        (PAYMENT_METHOD_OTHER, 'Other'),
    ]

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.SET_NULL,
        related_name='payments',
        null=True,
        blank=True,
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.SET_NULL,
        related_name='payments',
        null=True,
        blank=True,
    )
    tenant_name = models.CharField(max_length=160)
    property_name = models.CharField(max_length=160)
    amount_to_pay = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_date = models.DateField(null=True, blank=True)
    due_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_UNREMITTED)
    expected = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    bank_reference = models.CharField(max_length=120, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='recorded_payments',
        null=True,
        blank=True,
    )
    rent_period_start = models.DateField()
    rent_period_end = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-due_date', '-created_at']

    def clean(self):
        errors = {}

        if self.property:
            self.property_name = self.property.property_name

        if self.rent_period_start and self.rent_period_end and self.rent_period_start > self.rent_period_end:
            errors['rent_period_end'] = 'Rent period end must be on or after the rent period start.'

        if self.amount_paid is not None and self.amount_to_pay is not None and self.amount_paid > self.amount_to_pay:
            errors['amount_paid'] = 'Amount paid cannot be greater than the amount to pay.'

        if self.expected is not None and self.amount_to_pay is not None and self.expected > self.amount_to_pay:
            errors['expected'] = 'Expected amount cannot be greater than the amount to pay.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.tenant and not self.tenant_name:
            self.tenant_name = self.tenant.name

        if self.property:
            self.property_name = self.property.property_name

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.tenant_name} - {self.property_name} - {self.amount_paid}/{self.amount_to_pay}'
