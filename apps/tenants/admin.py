from django.contrib import admin

from .models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'email',
        'phone_number',
        'property',
        'apartment_type',
        'tenancy_type',
        'payment_mode',
        'payment_amount',
        'landlord_name',
    )
    list_filter = ('tenancy_type', 'payment_mode', 'apartment_type', 'landlord', 'property')
    search_fields = ('name', 'email', 'phone_number', 'apartment_type', 'landlord_name', 'property__property_name')
