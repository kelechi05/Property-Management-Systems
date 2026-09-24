from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator


class Landlord(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='landlord_profile',
    )
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    commission_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Percentage commission the landlord pays to the company (0-100%)',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__username']

    def __str__(self):
        display_name =  self.user.username 
        return f'Landlord: {display_name}'


class Property(models.Model):
    landlord = models.ForeignKey(
        Landlord,
        on_delete=models.CASCADE,
        related_name='managed_properties',
    )
    property_name = models.CharField(max_length=160)
    property_type = models.CharField(max_length=120)
    number_of_units = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    address = models.TextField()
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['property_name', '-created_at']

    def __str__(self):
        return f'{self.property_name} ({self.landlord.user.username or self.landlord.user.email})'
