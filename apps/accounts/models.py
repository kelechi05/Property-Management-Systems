from django.conf import settings
from django.db import models

from apps.properties.models import Landlord
from apps.tenants.models import Tenant


class UserProfile(models.Model):
    ROLE_USER = 'user'
    ROLE_STAFF = 'staff'
    ROLE_LANDLORD = 'landlord'
    ROLE_TENANT = 'tenant'

    ROLE_CHOICES = [
        (ROLE_USER, 'User'),
        (ROLE_STAFF, 'Staff'),
        (ROLE_LANDLORD, 'Landlord'),
        (ROLE_TENANT, 'Tenant'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_USER)

    def __str__(self):
        return f'{self.user.email or self.user.username} - {self.get_role_display()}'


class StaffProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='staff_profile',
    )
    phone_number = models.CharField(max_length=30, blank=True)
    job_title = models.CharField(max_length=120, blank=True)
    landlords = models.ManyToManyField(
        Landlord,
        related_name='assigned_staff',
        blank=True,
    )
    tenants = models.ManyToManyField(
        Tenant,
        related_name='assigned_staff',
        blank=True,
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__username']

    def __str__(self):
        return self.job_title or self.user.get_username() or self.user.email


class NotificationSeen(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='seen_notifications',
    )
    notification_key = models.CharField(max_length=255)
    seen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-seen_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'notification_key'],
                name='unique_seen_notification_per_user',
            )
        ]

    def __str__(self):
        return f'{self.user_id}:{self.notification_key}'
