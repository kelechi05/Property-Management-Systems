"""
Business logic services for the Property Management project.
"""

from calendar import monthrange

from apps.payments.models import Payment


def add_one_month(value):
    """Return the same calendar day in the next month, clamped to month-end."""
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def get_upcoming_rent_notifications(payments_qs, today):
    """
    Build reminder items for unpaid rent due between today and one month ahead.
    """
    reminder_end = add_one_month(today)
    upcoming_payments = (
        payments_qs.filter(
            status=Payment.STATUS_UNREMITTED,
            due_date__gte=today,
            due_date__lte=reminder_end,
        )
        .select_related('tenant', 'property')
        .order_by('due_date', 'tenant_name')
    )

    reminders = []
    for payment in upcoming_payments:
        reminders.append(
            {
                'payment': payment,
                'days_until_due': (payment.due_date - today).days,
                'outstanding_amount': payment.amount_to_pay - payment.amount_paid,
            }
        )

    return {
        'reminders': reminders,
        'reminder_end': reminder_end,
    }


class PropertyService:
    """Service for managing properties."""
    
    @staticmethod
    def create_property(owner, **kwargs):
        """Create a new property."""
        pass
    
    @staticmethod
    def update_property(property_id, **kwargs):
        """Update property details."""
        pass
    
    @staticmethod
    def delete_property(property_id):
        """Delete a property."""
        pass


class TenantService:
    """Service for managing tenants."""
    
    @staticmethod
    def register_tenant(user, **kwargs):
        """Register a new tenant."""
        pass
    
    @staticmethod
    def update_tenant(tenant_id, **kwargs):
        """Update tenant information."""
        pass


class PaymentService:
    """Service for processing payments."""
    
    @staticmethod
    def process_rent_payment(tenant, amount, property_id):
        """Process rent payment."""
        pass
    
    @staticmethod
    def generate_payment_receipt(payment):
        """Generate payment receipt."""
        pass


class LeaseService:
    """Service for managing leases."""
    
    @staticmethod
    def create_lease(property_id, tenant_id, **kwargs):
        """Create a new lease."""
        pass
    
    @staticmethod
    def terminate_lease(lease_id):
        """Terminate a lease."""
        pass


class MaintenanceService:
    """Service for managing maintenance requests."""
    
    @staticmethod
    def create_maintenance_request(property_id, description):
        """Create a maintenance request."""
        pass
    
    @staticmethod
    def assign_maintenance(request_id, contractor):
        """Assign maintenance to contractor."""
        pass
