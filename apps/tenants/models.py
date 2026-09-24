from django.db import models

from apps.properties.models import Landlord, Property


class Tenant(models.Model):
    TENANCY_TYPE_MONTHLY = 'monthly'
    TENANCY_TYPE_QUARTERLY = 'quarterly'
    TENANCY_TYPE_BIANNUALLY = 'biannually'
    TENANCY_TYPE_YEARLY = 'yearly'

    TENANCY_TYPE_CHOICES = [
        (TENANCY_TYPE_MONTHLY, 'Monthly'),
        (TENANCY_TYPE_QUARTERLY, 'Quarterly'),
        (TENANCY_TYPE_BIANNUALLY, 'Biannually'),
        (TENANCY_TYPE_YEARLY, 'Yearly'),
    ]

    PAYMENT_MODE_CASH = 'cash'
    PAYMENT_MODE_TRANSFER = 'transfer'
    PAYMENT_MODE_CARD = 'card'
    PAYMENT_MODE_OTHER = 'other'

    PAYMENT_MODE_CHOICES = [
        (PAYMENT_MODE_CASH, 'Cash'),
        (PAYMENT_MODE_TRANSFER, 'Transfer'),
        (PAYMENT_MODE_CARD, 'Card'),
        (PAYMENT_MODE_OTHER, 'Other'),
    ]

    name = models.CharField(max_length=160)
    phone_number = models.CharField(max_length=30)
    apartment_type = models.CharField(max_length=120)
    tenancy_type = models.CharField(
        max_length=20,
        choices=TENANCY_TYPE_CHOICES,
        default=TENANCY_TYPE_MONTHLY,
    )
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODE_CHOICES)
    address = models.TextField()
    email = models.EmailField()
    landlord = models.ForeignKey(
        Landlord,
        on_delete=models.SET_NULL,
        related_name='tenants',
        null=True,
        blank=True,
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.SET_NULL,
        related_name='tenants',
        null=True,
        blank=True,
    )
    landlord_name = models.CharField(max_length=160)
    payment_amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def clean(self):
        errors = {}

        if self.property_id and self.landlord_id and self.property.landlord_id != self.landlord_id:
            errors['property'] = 'The selected property must belong to the selected landlord.'

        if errors:
            from django.core.exceptions import ValidationError
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.property_id and not self.landlord_id:
            self.landlord = self.property.landlord

        if self.landlord and not self.landlord_name:
            self.landlord_name = self.landlord.user.username or self.landlord.user.email

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} - {self.apartment_type}'
