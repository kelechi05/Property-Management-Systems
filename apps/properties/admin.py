from django.contrib import admin

from .models import Landlord, Property


@admin.register(Landlord)
class LandlordAdmin(admin.ModelAdmin):
    list_display = ('user', 'email', 'phone_number', 'created_at')
    search_fields = ('user__username', 'user__email', 'email', 'phone_number')
    list_filter = ('created_at',)


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('property_name', 'landlord', 'property_type', 'number_of_units', 'city', 'state', 'created_at')
    search_fields = ('property_name', 'property_type', 'address', 'city', 'state', 'landlord__user__username')
    list_filter = ('property_type', 'created_at')
