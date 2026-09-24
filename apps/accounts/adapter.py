from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse

from .models import UserProfile


def get_user_role(user):
    if not user.is_authenticated:
        return UserProfile.ROLE_USER

    profile = getattr(user, 'profile', None)
    if profile and profile.role:
        return profile.role
    if user.is_staff:
        return UserProfile.ROLE_STAFF
    return UserProfile.ROLE_USER


def get_dashboard_url_for_user(user):
    role = get_user_role(user)
    route_map = {
        UserProfile.ROLE_USER: 'dashboard:pending_approval',
        UserProfile.ROLE_STAFF: 'dashboard:staff',
        UserProfile.ROLE_LANDLORD: 'dashboard:landlord',
        UserProfile.ROLE_TENANT: 'dashboard:tenant',
    }
    return reverse(route_map.get(role, 'dashboard:pending_approval'))


class RoleBasedAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        return get_dashboard_url_for_user(request.user)

    def get_signup_redirect_url(self, request):
        return get_dashboard_url_for_user(request.user)
