"""
Custom permission classes for the Property Management project.
"""
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin


class PropertyOwnerPermission(PermissionRequiredMixin):
    """Permission mixin for property owners."""
    permission_required = 'properties.view_property'
    redirect_field_name = 'next'
    login_url = 'admin:login'


class TenantPermission(PermissionRequiredMixin):
    """Permission mixin for tenants."""
    permission_required = 'tenants.view_tenant'
    redirect_field_name = 'next'
    login_url = 'admin:login'


def is_property_owner(user):
    """Check if user is a property owner."""
    return user.groups.filter(name='Property Owners').exists()


def is_tenant(user):
    """Check if user is a tenant."""
    return user.groups.filter(name='Tenants').exists()
