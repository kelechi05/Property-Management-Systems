from django.contrib import admin

from .models import MaintenanceReport


@admin.register(MaintenanceReport)
class MaintenanceReportAdmin(admin.ModelAdmin):
    list_display = (
        'display_label',
        'landlord',
        'tenant',
        'property',
        'priority',
        'status',
        'cost',
        'submitted_by',
        'created_at',
    )
    list_filter = ('status', 'priority', 'submitted_by', 'created_at')
    search_fields = (
        'description',
        'tenant__name',
        'property__property_name',
        'landlord__user__username',
        'landlord__user__email',
    )

    @admin.display(description='Label')
    def display_label(self, obj):
        return obj.display_label()
