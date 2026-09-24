from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import StaffProfile, UserProfile
from .utils import to_proper_case

User = get_user_model()


APPROVED_ROLES = {
    UserProfile.ROLE_STAFF,
    UserProfile.ROLE_LANDLORD,
    UserProfile.ROLE_TENANT,
}


@receiver(pre_save, sender=UserProfile)
def capture_previous_role(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_role = None
        return

    previous = sender.objects.filter(pk=instance.pk).values_list('role', flat=True).first()
    instance._previous_role = previous


@receiver(pre_save, sender=User)
def normalize_username(sender, instance, **kwargs):
    instance.username = to_proper_case(instance.username)


@receiver(post_save, sender=UserProfile)
def send_role_assignment_email(sender, instance, created, **kwargs):
    current_role = instance.role
    previous_role = getattr(instance, '_previous_role', None)

    if current_role not in APPROVED_ROLES:
        return

    if not created and previous_role == current_role:
        return

    if previous_role in APPROVED_ROLES and previous_role == current_role:
        return

    recipient = instance.user.email
    if not recipient:
        return

    subject = 'Your account has been approved'
    message = (
        f'Hello {instance.user.username or instance.user.email},\n\n'
        f'Your property management account has been approved as {instance.get_role_display()}.\n'
        'You can now sign in to access your dashboard.\n\n'
        'Sign in here: /accounts/login/\n\n'
        'Thank you.'
    )

    send_mail(
        subject,
        message,
        getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@propertymanagement.local'),
        [recipient],
        fail_silently=False,
    )


@receiver(post_save, sender=UserProfile)
def ensure_staff_profile(sender, instance, **kwargs):
    if instance.role == UserProfile.ROLE_STAFF:
        StaffProfile.objects.get_or_create(user=instance.user)
