from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'tenant_name',
        'property_name',
        'amount_to_pay',
        'amount_paid',
        'status',
        'payment_method',
        'due_date',
        'payment_date',
        'recorded_by',
    )
    readonly_fields = ('tenant_name', 'property_name')
    list_filter = ('status', 'payment_method', 'due_date', 'payment_date')
    search_fields = ('tenant_name', 'property_name', 'bank_reference', 'recorded_by__username', 'recorded_by__email')
