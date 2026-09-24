"""
Views for the authenticated dashboard.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO
import json

from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.urls import reverse
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.adapter import get_dashboard_url_for_user, get_user_role
from apps.accounts.models import NotificationSeen, StaffProfile, UserProfile
from apps.maintenance.models import MaintenanceReport
from apps.payments.models import Payment
from apps.properties.models import Property
from apps.tenants.models import Tenant
from core.services import get_upcoming_rent_notifications


class DashboardIndexView(LoginRequiredMixin, TemplateView):
    login_url = 'account_login'

    def get(self, request, *args, **kwargs):
        return redirect(get_dashboard_url_for_user(request.user))


class RoleDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'
    login_url = 'account_login'
    expected_role = None
    heading = 'Dashboard'
    intro = "Welcome back! Here's an overview of your property management activity."

    def dispatch(self, request, *args, **kwargs):
        if self.expected_role and get_user_role(request.user) != self.expected_role:
            return redirect(get_dashboard_url_for_user(request.user))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'dashboard_heading': self.heading,
                'dashboard_intro': self.intro,
                'dashboard_role': self.expected_role or get_user_role(self.request.user),
            }
        )
        return context


REPORT_DEFINITIONS = {
    'financial': {
        'title': 'Financial Report',
        'intro': 'Review rent billed, rent collected, and outstanding balances.',
    },
    'payment': {
        'title': 'Payment Report',
        'intro': 'Track payment records, statuses, and due dates.',
    },
    'occupancy': {
        'title': 'Occupancy Report',
        'intro': 'Monitor property coverage and tenant occupancy levels.',
    },
    'tenancy': {
        'title': 'Tenancy Report',
        'intro': 'Review tenant accounts and tenancy arrangements.',
    },
    'maintenance': {
        'title': 'Maintenance Report',
        'intro': 'Review complaints, work status, and maintenance costs across the portfolio.',
    },
}


def build_detail_field(label, value):
    return {'label': label, 'value': value if value not in (None, '') else 'Not provided'}


def build_rent_notification_item(reminder, destination_url, prefix='Rent'):
    days_until_due = reminder['days_until_due']
    payment = reminder['payment']
    return {
        'category': 'Rent',
        'key': f"rent:{payment.pk}:{payment.updated_at.isoformat()}",
        'title': f"{prefix} due in {days_until_due} day{'s' if days_until_due != 1 else ''}" if prefix == 'Rent' else f"{prefix} rent due in {days_until_due} day{'s' if days_until_due != 1 else ''}",
        'meta': f"Property: {payment.property_name} | Due: {payment.due_date} | Outstanding: {reminder['outstanding_amount']}",
        'detail': f"Tenant: {payment.tenant_name} | Property: {payment.property_name} | Due date: {payment.due_date} | Outstanding amount: {reminder['outstanding_amount']} | Payment status: {payment.get_status_display()}",
        'url': destination_url,
    }


def build_maintenance_notification_item(report, destination_url):
    return {
        'category': 'Maintenance',
        'key': f"maintenance:{report.pk}:{report.updated_at.isoformat()}",
        'title': report.display_label(),
        'meta': f"Status: {report.get_status_display()} | Priority: {report.get_priority_display()} | Cost: {report.cost or 'Not set'}",
        'detail': f"Description: {report.description}" + (
            f" | Staff note: {report.staff_note}" if report.staff_note else ''
        ),
        'url': destination_url,
    }


def apply_notification_seen_state(user, items):
    if not items:
        return [], []

    keys = [item['key'] for item in items]
    seen_keys = set(
        NotificationSeen.objects.filter(user=user, notification_key__in=keys).values_list(
            'notification_key', flat=True
        )
    )
    for item in items:
        item['is_unread'] = item['key'] not in seen_keys

    unread_items = [item for item in items if item['is_unread']]
    return items, unread_items


class UserDashboardView(RoleDashboardView):
    expected_role = 'user'
    heading = 'User Dashboard'
    intro = 'Manage your account activity and track the latest updates in one place.'


class PendingApprovalView(RoleDashboardView):
    template_name = 'dashboard/pending_approval.html'
    expected_role = 'user'
    heading = 'Pending Approval'
    intro = 'Your account is waiting for admin approval before dashboard access is enabled.'


class StaffDashboardView(RoleDashboardView):
    template_name = 'dashboard/staff.html'
    expected_role = 'staff'
    heading = 'Staff Dashboard'
    intro = 'Review daily operations, follow tasks, and keep team workflows moving.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        staff_profile = (
            StaffProfile.objects.filter(user=self.request.user)
            .prefetch_related('landlords__user', 'tenants__landlord__user')
            .first()
        )

        if staff_profile is None:
            managed_landlords = []
            managed_tenants = []
            managed_properties_count = 0
            managed_payments_count = 0
            maintenance_reports = MaintenanceReport.objects.none()
        else:
            managed_landlords = list(staff_profile.landlords.all())
            managed_tenants = list(staff_profile.tenants.all())
            managed_properties_count = Property.objects.filter(
                landlord__in=managed_landlords
            ).count()
            managed_payments_qs = Payment.objects.filter(
                Q(tenant__in=managed_tenants) | Q(property__landlord__in=managed_landlords)
            ).distinct()
            managed_payments_count = managed_payments_qs.count()
            upcoming_rent_data = get_upcoming_rent_notifications(managed_payments_qs, today)
            maintenance_reports = (
                MaintenanceReport.objects.select_related('tenant', 'property', 'landlord__user', 'assigned_staff')
                .filter(Q(tenant__in=managed_tenants) | Q(landlord__in=managed_landlords))
                .distinct()
                .order_by('-created_at')
            )

        if staff_profile is None:
            upcoming_rent_data = {'reminders': [], 'reminder_end': None}
            maintenance_notifications = []
        else:
            maintenance_notifications = list(
                maintenance_reports.exclude(status=MaintenanceReport.STATUS_CLOSED)[:5]
            )
        maintenance_page_url = reverse('maintenance:staff-list')
        rent_page_url = reverse('accounts:staff-payment-list')
        notification_items = [
            build_rent_notification_item(
                reminder,
                destination_url=rent_page_url,
                prefix=reminder['payment'].tenant_name,
            )
            for reminder in upcoming_rent_data['reminders']
        ]
        notification_items.extend(
            [
                build_maintenance_notification_item(report, maintenance_page_url)
                for report in maintenance_notifications
            ]
        )
        notification_items, unread_notification_items = apply_notification_seen_state(
            self.request.user,
            notification_items,
        )

        context.update(
            {
                'managed_landlords': managed_landlords,
                'managed_tenants': managed_tenants,
                'managed_landlords_count': len(managed_landlords),
                'managed_tenants_count': len(managed_tenants),
                'managed_properties_count': managed_properties_count,
                'managed_payments_count': managed_payments_count,
                'managed_records_count': len(managed_landlords) + len(managed_tenants),
                'rent_due_notifications': upcoming_rent_data['reminders'],
                'rent_due_notification_count': len(upcoming_rent_data['reminders']),
                'rent_due_notification_end': upcoming_rent_data['reminder_end'],
                'maintenance_report_count': maintenance_reports.count(),
                'maintenance_open_count': maintenance_reports.filter(
                    status__in=[MaintenanceReport.STATUS_NEW, MaintenanceReport.STATUS_IN_PROGRESS]
                ).count(),
                'maintenance_notifications': maintenance_notifications,
                'maintenance_notification_count': len(maintenance_notifications),
                'dashboard_notification_items': unread_notification_items,
                'dashboard_notification_count': len(unread_notification_items),
                'dashboard_notification_bell_url': maintenance_page_url,
            }
        )
        return context


class LandlordDashboardView(RoleDashboardView):
    template_name = 'dashboard/landlord.html'
    expected_role = 'landlord'
    heading = 'Landlord Dashboard'
    intro = 'Monitor your properties, tenants, and rent activity from a single dashboard.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        landlord = getattr(self.request.user, 'landlord_profile', None)
        today = timezone.localdate()

        if landlord is None:
            total_properties_count = 0
            occupied_units_count = 0
            outstanding_rent = Decimal('0.00')
            recent_payments = []
            payments_count = 0
            maintenance_reports = MaintenanceReport.objects.none()
            upcoming_rent_data = {'reminders': [], 'reminder_end': None}
        else:
            total_properties_count = Property.objects.filter(landlord=landlord).count()
            occupied_units_count = Tenant.objects.filter(landlord=landlord).count()
            remitted_payments_qs = (
                Payment.objects.filter(
                    property__landlord=landlord,
                    status=Payment.STATUS_REMITTED,
                )
                .select_related('tenant', 'property', 'recorded_by')
            )
            recent_payments = list(remitted_payments_qs.order_by('-payment_date', '-created_at')[:5])
            payments_count = remitted_payments_qs.count()
            upcoming_rent_data = {'reminders': [], 'reminder_end': None}
            outstanding_rent = Decimal('0.00')
            maintenance_reports = (
                MaintenanceReport.objects.select_related('tenant', 'property', 'assigned_staff')
                .filter(landlord=landlord)
                .order_by('-created_at')
            )
        maintenance_page_url = reverse('maintenance:landlord-list')
        rent_page_url = reverse('dashboard:landlord-payments')
        maintenance_notifications = list(
            maintenance_reports.exclude(status=MaintenanceReport.STATUS_CLOSED)[:5]
        )
        notification_items = [
            build_rent_notification_item(
                reminder,
                destination_url=rent_page_url,
                prefix=reminder['payment'].tenant_name,
            )
            for reminder in upcoming_rent_data['reminders']
        ]
        notification_items.extend(
            [
                build_maintenance_notification_item(report, maintenance_page_url)
                for report in maintenance_notifications
            ]
        )
        notification_items, unread_notification_items = apply_notification_seen_state(
            self.request.user,
            notification_items,
        )

        context.update(
            {
                'total_properties_count': total_properties_count,
                'occupied_units_count': occupied_units_count,
                'outstanding_rent': outstanding_rent,
                'recent_payments': recent_payments,
                'payments_count': payments_count,
                'maintenance_report_count': maintenance_reports.count(),
                'maintenance_open_count': maintenance_reports.filter(
                    status__in=[MaintenanceReport.STATUS_NEW, MaintenanceReport.STATUS_IN_PROGRESS]
                ).count(),
                'maintenance_notifications': maintenance_notifications,
                'dashboard_notification_items': unread_notification_items,
                'dashboard_notification_count': len(unread_notification_items),
                'dashboard_notification_bell_url': maintenance_page_url,
            }
        )
        return context


class TenantDashboardView(RoleDashboardView):
    template_name = 'dashboard/tenant.html'
    expected_role = 'tenant'
    heading = 'Tenant Dashboard'
    intro = 'Check your tenancy information, payments, and property-related updates here.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_record = Tenant.objects.filter(email__iexact=self.request.user.email).select_related('landlord', 'landlord__user').first()
        today = timezone.localdate()

        if tenant_record is None:
            current_rent = Decimal('0.00')
            payment_history = []
            upcoming_rent_data = {'reminders': [], 'reminder_end': None}
            maintenance_reports = MaintenanceReport.objects.none()
        else:
            payments_qs = Payment.objects.filter(tenant=tenant_record).select_related('property', 'recorded_by')
            payment_history = list(payments_qs.order_by('-payment_date', '-created_at')[:5])
            current_rent = tenant_record.payment_amount
            upcoming_rent_data = get_upcoming_rent_notifications(payments_qs, today)
            maintenance_reports = (
                MaintenanceReport.objects.select_related('property', 'assigned_staff')
                .filter(tenant=tenant_record)
                .order_by('-created_at')
            )
        maintenance_page_url = reverse('maintenance:tenant-list')
        rent_page_url = reverse('dashboard:tenant-payments')
        maintenance_notifications = list(
            maintenance_reports.exclude(status=MaintenanceReport.STATUS_CLOSED)[:5]
        )
        notification_items = [
            build_rent_notification_item(reminder, rent_page_url)
            for reminder in upcoming_rent_data['reminders']
        ]
        notification_items.extend(
            [
                build_maintenance_notification_item(report, maintenance_page_url)
                for report in maintenance_notifications
            ]
        )
        notification_items, unread_notification_items = apply_notification_seen_state(
            self.request.user,
            notification_items,
        )

        context.update(
            {
                'tenant_record': tenant_record,
                'current_rent': current_rent,
                'payment_history': payment_history,
                'rent_due_notifications': upcoming_rent_data['reminders'],
                'rent_due_notification_count': len(upcoming_rent_data['reminders']),
                'rent_due_notification_end': upcoming_rent_data['reminder_end'],
                'maintenance_report_count': maintenance_reports.count(),
                'recent_maintenance_reports': list(maintenance_reports[:5]),
                'dashboard_notification_items': unread_notification_items,
                'dashboard_notification_count': len(unread_notification_items),
                'dashboard_notification_bell_url': maintenance_page_url,
            }
        )
        return context


class LandlordPaymentReportView(RoleDashboardView):
    template_name = 'dashboard/landlord_payments.html'
    expected_role = UserProfile.ROLE_LANDLORD
    heading = 'Landlord Payments'
    intro = 'Review rent collections, outstanding balances, and recent payment activity.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        landlord = getattr(self.request.user, 'landlord_profile', None)

        if landlord is None:
            payments = Payment.objects.none()
        else:
            payments = (
                Payment.objects.filter(
                    property__landlord=landlord,
                    status=Payment.STATUS_REMITTED,
                )
                .select_related('tenant', 'property', 'recorded_by')
                .order_by('-due_date', '-created_at')
            )

        context.update(
            {
                'payment_report': payments,
                'payment_report_count': payments.count(),
            }
        )
        return context


class TenantPaymentReportView(RoleDashboardView):
    template_name = 'dashboard/tenant_payments.html'
    expected_role = UserProfile.ROLE_TENANT
    heading = 'Tenant Payments'
    intro = 'See your rent history, due dates, and the latest payment updates.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_record = Tenant.objects.filter(email__iexact=self.request.user.email).first()

        if tenant_record is None:
            payments = Payment.objects.none()
        else:
            payments = (
                Payment.objects.filter(tenant=tenant_record)
                .select_related('property', 'recorded_by')
                .order_by('-due_date', '-created_at')
            )

        context.update(
            {
                'tenant_record': tenant_record,
                'payment_report': payments,
                'payment_report_count': payments.count(),
            }
        )
        return context


class LandlordPaymentDetailView(RoleDashboardView):
    template_name = 'dashboard/payment_detail.html'
    expected_role = UserProfile.ROLE_LANDLORD
    heading = 'Payment Details'
    intro = 'Review the full rent record for this payment entry.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        landlord = getattr(self.request.user, 'landlord_profile', None)
        payment = get_object_or_404(
            Payment.objects.select_related('tenant', 'property', 'recorded_by'),
            pk=self.kwargs['pk'],
            property__landlord=landlord,
            status=Payment.STATUS_REMITTED,
        )

        context.update(
            {
                'base_template': 'dashboard/landlord_base.html',
                'page_heading': f'Payment Record #{payment.pk}',
                'page_intro': 'Complete payment information for your tenant and property.',
                'back_url': reverse('dashboard:landlord-payments'),
                'back_label': 'Back to payment list',
                'summary_cards': [
                    {'label': 'Status', 'value': payment.get_status_display()},
                    {'label': 'Amount To Pay', 'value': payment.amount_to_pay},
                    {'label': 'Outstanding', 'value': payment.amount_to_pay - payment.amount_paid},
                ],
                'detail_sections': [
                    {
                        'title': 'Payment Information',
                        'fields': [
                            build_detail_field('Tenant Name', payment.tenant_name),
                            build_detail_field('Property Name', payment.property_name),
                            build_detail_field('Amount To Pay', payment.amount_to_pay),
                            build_detail_field('Expected Amount', payment.expected),
                            build_detail_field('Status', payment.get_status_display()),
                            build_detail_field('Payment Method', payment.get_payment_method_display()),
                            build_detail_field('Bank Reference', payment.bank_reference),
                        ],
                    },
                    {
                        'title': 'Schedule and Audit',
                        'fields': [
                            build_detail_field('Due Date', payment.due_date),
                            build_detail_field('Payment Date', payment.payment_date),
                            build_detail_field('Rent Period Start', payment.rent_period_start),
                            build_detail_field('Rent Period End', payment.rent_period_end),
                            build_detail_field(
                                'Recorded By',
                                payment.recorded_by.username if payment.recorded_by else 'Not recorded',
                            ),
                            build_detail_field('Created At', payment.created_at),
                            build_detail_field('Updated At', payment.updated_at),
                        ],
                    },
                ],
            }
        )
        return context


class TenantPaymentDetailView(RoleDashboardView):
    template_name = 'dashboard/payment_detail.html'
    expected_role = UserProfile.ROLE_TENANT
    heading = 'Payment Details'
    intro = 'Review the full rent record for this payment entry.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_record = get_object_or_404(Tenant, email__iexact=self.request.user.email)
        payment = get_object_or_404(
            Payment.objects.select_related('tenant', 'property', 'recorded_by'),
            pk=self.kwargs['pk'],
            tenant=tenant_record,
        )

        context.update(
            {
                'base_template': 'dashboard/tenant_base.html',
                'page_heading': f'Payment Record #{payment.pk}',
                'page_intro': 'Complete payment information for your rent record.',
                'back_url': reverse('dashboard:tenant-payments'),
                'back_label': 'Back to payment list',
                'summary_cards': [
                    {'label': 'Status', 'value': payment.get_status_display()},
                    {'label': 'Amount To Pay', 'value': payment.amount_to_pay},
                    {'label': 'Outstanding', 'value': payment.amount_to_pay - payment.amount_paid},
                ],
                'detail_sections': [
                    {
                        'title': 'Payment Information',
                        'fields': [
                            build_detail_field('Tenant Name', payment.tenant_name),
                            build_detail_field('Property Name', payment.property_name),
                            build_detail_field('Amount To Pay', payment.amount_to_pay),
                            build_detail_field('Expected Amount', payment.expected),
                            build_detail_field('Status', payment.get_status_display()),
                            build_detail_field('Payment Method', payment.get_payment_method_display()),
                            build_detail_field('Bank Reference', payment.bank_reference),
                        ],
                    },
                    {
                        'title': 'Schedule and Audit',
                        'fields': [
                            build_detail_field('Due Date', payment.due_date),
                            build_detail_field('Payment Date', payment.payment_date),
                            build_detail_field('Rent Period Start', payment.rent_period_start),
                            build_detail_field('Rent Period End', payment.rent_period_end),
                            build_detail_field(
                                'Recorded By',
                                payment.recorded_by.username if payment.recorded_by else 'Not recorded',
                            ),
                            build_detail_field('Created At', payment.created_at),
                            build_detail_field('Updated At', payment.updated_at),
                        ],
                    },
                ],
            }
        )
        return context


class BaseReportView(RoleDashboardView):
    template_name = 'dashboard/report_detail.html'
    report_definitions = REPORT_DEFINITIONS

    def get_report_key(self):
        report_key = self.kwargs.get('report_type')
        if report_key not in self.report_definitions:
            raise Http404('Unknown report type.')
        return report_key

    def get_base_queryset_data(self):
        raise NotImplementedError

    def get_financial_filter_values(self):
        return {
            'start_date': self.request.GET.get('start_date', '').strip(),
            'end_date': self.request.GET.get('end_date', '').strip(),
            'property': self.request.GET.get('property', '').strip(),
            'status': self.request.GET.get('status', '').strip(),
        }

    def apply_financial_filters(self, payments):
        filter_values = self.get_financial_filter_values()
        filtered_payments = payments
        active_filters = []

        start_date = filter_values['start_date']
        end_date = filter_values['end_date']
        property_filter = filter_values['property']
        status_filter = filter_values['status']

        if start_date:
            try:
                parsed_start = date.fromisoformat(start_date)
                filtered_payments = [
                    payment for payment in filtered_payments if payment.due_date >= parsed_start
                ]
                active_filters.append(f'From: {parsed_start}')
            except ValueError:
                active_filters.append('Start date ignored because it is invalid.')

        if end_date:
            try:
                parsed_end = date.fromisoformat(end_date)
                filtered_payments = [
                    payment for payment in filtered_payments if payment.due_date <= parsed_end
                ]
                active_filters.append(f'To: {parsed_end}')
            except ValueError:
                active_filters.append('End date ignored because it is invalid.')

        if property_filter:
            try:
                property_id = int(property_filter)
                filtered_payments = [
                    payment for payment in filtered_payments
                    if payment.property_id == property_id or (
                        payment.tenant is not None and payment.tenant.property_id == property_id
                    )
                ]
                active_filters.append(f'Property: {property_filter}')
            except (ValueError, TypeError):
                active_filters.append('Property filter ignored because it is invalid.')

        if status_filter:
            filtered_payments = [
                payment for payment in filtered_payments if payment.status == status_filter
            ]
            status_display = dict(Payment.STATUS_CHOICES).get(status_filter, status_filter)
            active_filters.append(f'Status: {status_display}')

        return filtered_payments, filter_values, active_filters

    def get_occupancy_filter_values(self):
        return {
            'landlord': self.request.GET.get('landlord', '').strip(),
            'property': self.request.GET.get('property', '').strip(),
        }

    def get_payment_filter_values(self):
        return {
            'start_date': self.request.GET.get('start_date', '').strip(),
            'end_date': self.request.GET.get('end_date', '').strip(),
            'property': self.request.GET.get('property', '').strip(),
        }

    def apply_occupancy_filters(self, properties, tenants):
        filter_values = self.get_occupancy_filter_values()
        filtered_properties = list(properties)
        filtered_tenants = list(tenants)
        active_filters = []

        landlord_filter = filter_values['landlord']
        property_filter = filter_values['property']

        if landlord_filter:
            try:
                landlord_id = int(landlord_filter)
                filtered_properties = [
                    property for property in filtered_properties if property.landlord_id == landlord_id
                ]
                allowed_property_ids = {property.id for property in filtered_properties}
                filtered_tenants = [
                    tenant for tenant in filtered_tenants if tenant.property_id in allowed_property_ids
                ]
                landlord_match = next(
                    (property.landlord for property in filtered_properties if property.landlord_id == landlord_id),
                    None,
                )
                landlord_label = (
                    getattr(landlord_match.user, 'username', '') or getattr(landlord_match.user, 'email', '')
                    if landlord_match is not None
                    else landlord_filter
                )
                active_filters.append(f'Landlord: {landlord_label}')
            except (ValueError, TypeError):
                active_filters.append('Landlord filter ignored because it is invalid.')

        if property_filter:
            try:
                property_id = int(property_filter)
                filtered_properties = [
                    property for property in filtered_properties if property.id == property_id
                ]
                allowed_property_ids = {property.id for property in filtered_properties}
                filtered_tenants = [
                    tenant for tenant in filtered_tenants if tenant.property_id in allowed_property_ids
                ]
                property_match = next(
                    (property for property in filtered_properties if property.id == property_id),
                    None,
                )
                property_label = (
                    property_match.property_name if property_match is not None else property_filter
                )
                active_filters.append(f'Property: {property_label}')
            except (ValueError, TypeError):
                active_filters.append('Property filter ignored because it is invalid.')

        return filtered_properties, filtered_tenants, filter_values, active_filters

    def apply_payment_filters(self, payments):
        filter_values = self.get_payment_filter_values()
        filtered_payments = list(payments)
        active_filters = []
        start_date = filter_values['start_date']
        end_date = filter_values['end_date']
        property_filter = filter_values['property']

        if start_date:
            try:
                parsed_start = date.fromisoformat(start_date)
                filtered_payments = [
                    payment for payment in filtered_payments if payment.due_date >= parsed_start
                ]
                active_filters.append(f'From: {parsed_start}')
            except ValueError:
                active_filters.append('Start date ignored because it is invalid.')

        if end_date:
            try:
                parsed_end = date.fromisoformat(end_date)
                filtered_payments = [
                    payment for payment in filtered_payments if payment.due_date <= parsed_end
                ]
                active_filters.append(f'To: {parsed_end}')
            except ValueError:
                active_filters.append('End date ignored because it is invalid.')

        if property_filter:
            try:
                property_id = int(property_filter)
                filtered_payments = [
                    payment for payment in filtered_payments
                    if payment.property_id == property_id or (
                        payment.tenant is not None and payment.tenant.property_id == property_id
                    )
                ]
                property_match = next(
                    (
                        payment.property for payment in filtered_payments
                        if payment.property_id == property_id and payment.property is not None
                    ),
                    None,
                )
                property_label = (
                    property_match.property_name if property_match is not None else property_filter
                )
                active_filters.append(f'Property: {property_label}')
            except (ValueError, TypeError):
                active_filters.append('Property filter ignored because it is invalid.')

        return filtered_payments, filter_values, active_filters

    def build_report_context(self, report_key, scoped_data):
        payments = scoped_data['payments']
        tenants = scoped_data['tenants']
        properties = scoped_data['properties']
        maintenance_reports = scoped_data.get('maintenance_reports', [])

        if report_key == 'financial':
            payments, filter_values, active_filters = self.apply_financial_filters(payments)
            total_billed = sum((payment.amount_to_pay for payment in payments), Decimal('0.00'))
            total_collected = sum((payment.amount_paid for payment in payments), Decimal('0.00'))
            
            # Calculate total commission
            total_commission = Decimal('0.00')
            remitted_total = Decimal('0.00')
            unremitted_total = Decimal('0.00')
            report_rows = []
            for payment in payments:
                # Get commission percentage from landlord
                commission_percentage = Decimal('0.00')
                if payment.property and payment.property.landlord:
                    commission_percentage = Decimal(str(payment.property.landlord.commission_percentage or 0))
                
                # Calculate commission on amount paid
                commission_amount = (payment.amount_paid * commission_percentage ).quantize(Decimal('0.01'))
                amount_after_commission = payment.amount_paid - commission_amount
                total_commission += commission_amount
                if payment.status == Payment.STATUS_REMITTED:
                    remitted_total += amount_after_commission
                elif payment.status == Payment.STATUS_UNREMITTED:
                    unremitted_total += amount_after_commission

                property_name = (
                    payment.tenant.property.property_name
                    if payment.tenant is not None and payment.tenant.property is not None
                    else payment.property_name
                )
                report_rows.append([
                    payment.tenant_name,
                    property_name,
                    payment.amount_to_pay,
                    commission_amount,
                    amount_after_commission,
                    payment.get_status_display(),
                    payment.due_date,
                ])
            
            return {
                'report_summary_cards': [
                    {'label': 'Total Billed', 'value': total_billed},
                    {'label': 'Remitted Total', 'value': remitted_total},
                    {'label': 'Unremitted Total', 'value': unremitted_total},
                    {'label': 'Total Commission', 'value': total_commission},
                ],
                'report_headers': ['Tenant', 'Property', 'Amount To Pay', 'Commission', 'Amount After Commission', 'Status', 'Due Date'],
                'report_rows': report_rows,
                'report_empty_message': 'No financial records are available yet.',
                'financial_filter_values': filter_values,
                'financial_active_filters': active_filters,
            }

        if report_key == 'payment':
            payments, filter_values, active_filters = self.apply_payment_filters(payments)
            return {
                'report_summary_cards': [
                    {'label': 'Payment Records', 'value': len(payments)},
                    {'label': 'Remitted Records', 'value': len([payment for payment in payments if payment.status == Payment.STATUS_REMITTED])},
                ],
                'report_headers': ['Tenant', 'Property', 'Status', 'Amount To Pay', 'Due Date', 'Payment Date'],
                'report_rows': [
                    [
                        payment.tenant_name,
                        (
                            payment.tenant.property.property_name
                            if payment.tenant is not None and payment.tenant.property is not None
                            else payment.property_name
                        ),
                        payment.get_status_display(),
                        payment.amount_to_pay,
                        payment.due_date,
                        payment.payment_date or '-',
                    ]
                    for payment in payments
                ],
                'report_empty_message': 'No payment records are available yet.',
                'payment_filter_values': filter_values,
                'payment_active_filters': active_filters,
            }

        if report_key == 'occupancy':
            properties, tenants, filter_values, active_filters = self.apply_occupancy_filters(
                properties,
                tenants,
            )
            occupied_units = len([tenant for tenant in tenants if tenant.property_id])
            total_properties = len(properties)
            total_units = sum(property.number_of_units for property in properties)
            occupancy_rate = f"{round((occupied_units / total_units) * 100)}%" if total_units else '0%'
            occupied_units_by_property = {}

            for tenant in tenants:
                if not tenant.property_id:
                    continue

                occupied_units_by_property.setdefault(tenant.property_id, 0)
                occupied_units_by_property[tenant.property_id] += 1

            property_rows = [
                [
                    property.property_name,
                    property.property_type,
                    occupied_units_by_property.get(property.id, 0),
                    property.number_of_units - occupied_units_by_property.get(property.id, 0),
                    property.address,
                    getattr(property.landlord.user, 'username', '') or getattr(property.landlord.user, 'email', ''),
                ]
                for property in properties
            ]
            return {
                'report_summary_cards': [
                    {'label': 'Managed Properties', 'value': total_properties},
                    {'label': 'Occupied Units', 'value': occupied_units},
                    {'label': 'Occupancy Rate', 'value': occupancy_rate},
                ],
                'report_headers': ['Property', 'Type', 'Occupied Units', 'Available Units', 'Address', 'Landlord'],
                'report_rows': property_rows,
                'report_empty_message': 'No properties are available for occupancy reporting yet.',
                'occupancy_filter_values': filter_values,
                'occupancy_active_filters': active_filters,
            }

        if report_key == 'tenancy':
            tenant_rows = [
                [
                    tenant.name,
                    tenant.apartment_type,
                    tenant.get_tenancy_type_display(),
                    tenant.payment_amount,
                    tenant.landlord_name,
                ]
                for tenant in tenants
            ]
            return {
                'report_summary_cards': [
                    {'label': 'Tenant Records', 'value': len(tenants)},
                    {'label': 'Monthly Tenancies', 'value': len([tenant for tenant in tenants if tenant.tenancy_type == Tenant.TENANCY_TYPE_MONTHLY])},
                    {'label': 'Yearly Tenancies', 'value': len([tenant for tenant in tenants if tenant.tenancy_type == Tenant.TENANCY_TYPE_YEARLY])},
                ],
                'report_headers': ['Tenant', 'Apartment', 'Tenancy Type', 'Rent Amount', 'Landlord'],
                'report_rows': tenant_rows,
                'report_empty_message': 'No tenancy records are available yet.',
            }

        open_count = len(
            [report for report in maintenance_reports if report.status == MaintenanceReport.STATUS_NEW]
        )
        in_progress_count = len(
            [report for report in maintenance_reports if report.status == MaintenanceReport.STATUS_IN_PROGRESS]
        )
        completed_count = len(
            [
                report for report in maintenance_reports
                if report.status in {MaintenanceReport.STATUS_RESOLVED, MaintenanceReport.STATUS_CLOSED}
            ]
        )
        total_cost = sum(
            ((report.cost or Decimal('0.00')) for report in maintenance_reports),
            Decimal('0.00'),
        )
        return {
            'report_summary_cards': [
                {'label': 'New Complaints', 'value': open_count},
                {'label': 'In Progress', 'value': in_progress_count},
                {'label': 'Completed', 'value': completed_count},
                {'label': 'Total Cost', 'value': total_cost},
            ],
            'report_headers': ['Title', 'Tenant', 'Property', 'Priority', 'Status', 'Cost', 'Submitted By', 'Created'],
            'report_rows': [
                [
                    report.display_label(),
                    report.tenant.name if report.tenant else '-',
                    report.property.property_name if report.property else '-',
                    report.get_priority_display(),
                    report.get_status_display(),
                    report.cost or Decimal('0.00'),
                    report.get_submitted_by_display(),
                    timezone.localtime(report.created_at).date(),
                ]
                for report in maintenance_reports
            ],
            'report_empty_message': 'No maintenance reports are available yet.',
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report_key = self.get_report_key()
        report_meta = self.report_definitions[report_key]
        scoped_data = self.get_base_queryset_data()
        report_context = self.build_report_context(report_key, scoped_data)

        context.update(
            {
                'report_key': report_key,
                'report_title': report_meta['title'],
                'report_intro': report_meta['intro'],
                'financial_filter_values': {
                    'start_date': '',
                    'end_date': '',
                    'property': '',
                    'status': '',
                },
                'financial_active_filters': [],
                'financial_properties': scoped_data.get('properties', []),
                'financial_status_choices': Payment.STATUS_CHOICES,
                'payment_filter_values': {
                    'start_date': '',
                    'end_date': '',
                    'property': '',
                },
                'payment_active_filters': [],
                'payment_properties': scoped_data.get('properties', []),
                'occupancy_filter_values': {
                    'landlord': '',
                    'property': '',
                },
                'occupancy_active_filters': [],
                'occupancy_landlords': list(
                    {
                        property.landlord_id: property.landlord
                        for property in scoped_data.get('properties', [])
                    }.values()
                ),
                'occupancy_properties': scoped_data.get('properties', []),
                **report_context,
            }
        )
        return context


class StaffReportView(BaseReportView):
    expected_role = UserProfile.ROLE_STAFF
    heading = 'Staff Reports'
    intro = 'Review operational and financial reports for your assigned portfolio.'

    def get_base_queryset_data(self):
        staff_profile = StaffProfile.objects.filter(user=self.request.user).first()
        if staff_profile is None:
            return {
                'payments': [],
                'tenants': [],
                'properties': [],
                'maintenance_reports': [],
            }

        landlords = staff_profile.landlords.all()
        tenants = list(
            staff_profile.tenants.select_related('landlord', 'landlord__user', 'property').all()
        )
        properties = list(
            Property.objects.select_related('landlord', 'landlord__user')
            .filter(landlord__in=landlords)
            .order_by('property_name')
        )
        payments = list(
            Payment.objects.select_related('tenant', 'property', 'property__landlord', 'property__landlord__user')
            .filter(Q(tenant__in=staff_profile.tenants.all()) | Q(property__landlord__in=landlords))
            .distinct()
            .order_by('-due_date', '-created_at')
        )
        maintenance_reports = list(
            MaintenanceReport.objects.select_related('tenant', 'property', 'landlord__user', 'assigned_staff')
            .filter(Q(tenant__in=staff_profile.tenants.all()) | Q(landlord__in=landlords))
            .distinct()
            .order_by('-created_at')
        )
        return {
            'payments': payments,
            'tenants': tenants,
            'properties': properties,
            'maintenance_reports': maintenance_reports,
        }


class LandlordReportView(BaseReportView):
    expected_role = UserProfile.ROLE_LANDLORD
    heading = 'Landlord Reports'
    intro = 'Review reporting across your properties, tenants, and rent activity.'

    def get_base_queryset_data(self):
        landlord = getattr(self.request.user, 'landlord_profile', None)
        if landlord is None:
            return {
                'payments': [],
                'tenants': [],
                'properties': [],
                'maintenance_reports': [],
            }

        payments = list(
            Payment.objects.select_related('tenant', 'property', 'property__landlord', 'property__landlord__user')
            .filter(
                property__landlord=landlord,
                status=Payment.STATUS_REMITTED,
            )
            .order_by('-due_date', '-created_at')
        )
        tenants = list(
            Tenant.objects.select_related('landlord', 'landlord__user', 'property')
            .filter(landlord=landlord)
            .order_by('name')
        )
        properties = list(
            Property.objects.select_related('landlord', 'landlord__user')
            .filter(landlord=landlord)
            .order_by('property_name')
        )
        maintenance_reports = list(
            MaintenanceReport.objects.select_related('tenant', 'property', 'assigned_staff')
            .filter(landlord=landlord)
            .order_by('-created_at')
        )
        return {
            'payments': payments,
            'tenants': tenants,
            'properties': properties,
            'maintenance_reports': maintenance_reports,
        }


@login_required
def dashboard_index(request):
    """Redirect users to the dashboard that matches their role."""
    return redirect(get_dashboard_url_for_user(request.user))


def export_financial_report_to_excel(report_data, filename='financial_report.xlsx'):
    """Export financial report data to Excel."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    
    wb = Workbook()
    ws = wb.active
    ws.title = 'Financial Report'

    # Set column widths
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 15

    # Define styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    summary_fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
    summary_font = Font(bold=True)

    # Add title
    ws['A1'] = 'Financial Report'
    ws['A1'].font = Font(bold=True, size=14)
    ws.merge_cells('A1:F1')

    # Add summary section
    row = 3
    ws[f'A{row}'] = 'Summary'
    ws[f'A{row}'].font = Font(bold=True, size=12)

    row += 1
    summary_cards = report_data.get('report_summary_cards', [])
    for card in summary_cards:
        ws[f'A{row}'] = card['label']
        ws[f'B{row}'] = card['value']
        ws[f'A{row}'].font = summary_font
        ws[f'B{row}'].font = summary_font
        ws[f'A{row}'].fill = summary_fill
        ws[f'B{row}'].fill = summary_fill
        row += 1

    # Add filters section
    row += 1
    ws[f'A{row}'] = 'Filters Applied'
    ws[f'A{row}'].font = Font(bold=True, size=11)
    row += 1

    active_filters = report_data.get('financial_active_filters', [])
    for filter_text in active_filters:
        ws[f'A{row}'] = filter_text
        row += 1

    # Add table data
    row += 1
    headers = report_data.get('report_headers', [])
    
    # Write headers
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col_idx)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = border

    row += 1
    rows_data = report_data.get('report_rows', [])
    for row_data in rows_data:
        for col_idx, cell_value in enumerate(row_data, 1):
            cell = ws.cell(row=row, column=col_idx)
            cell.value = str(cell_value)
            cell.border = border
            cell.alignment = Alignment(horizontal="left", vertical="center")
            if col_idx in [3, 4]:  # Amount columns
                cell.alignment = Alignment(horizontal="right", vertical="center")
        row += 1

    # Save to BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def export_financial_report_to_pdf(report_data, filename='financial_report.pdf'):
    """Export financial report data to PDF."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(letter))
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#366092'),
        spaceAfter=12,
        alignment=1
    )
    elements.append(Paragraph('Financial Report', title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Summary Cards
    summary_heading = ParagraphStyle(
        'SummaryHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#366092'),
        spaceAfter=6
    )
    elements.append(Paragraph('Summary', summary_heading))
    
    summary_cards = report_data.get('report_summary_cards', [])
    summary_data = []
    for card in summary_cards:
        summary_data.append([card['label'], str(card['value'])])
    
    if summary_data:
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(summary_table)
    
    elements.append(Spacer(1, 0.2*inch))
    
    # Active Filters
    active_filters = report_data.get('financial_active_filters', [])
    if active_filters:
        elements.append(Paragraph('Filters Applied', summary_heading))
        filters_data = [[f] for f in active_filters]
        filters_table = Table(filters_data, colWidths=[5*inch])
        filters_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightyellow),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(filters_table)
        elements.append(Spacer(1, 0.2*inch))
    
    # Data Table
    headers = report_data.get('report_headers', [])
    rows_data = report_data.get('report_rows', [])
    
    if headers and rows_data:
        table_data = [headers] + [[str(cell) for cell in row] for row in rows_data]
        
        # Calculate column widths based on number of columns
        col_width = 7.5 * inch / len(headers)
        col_widths = [col_width] * len(headers)
        
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        elements.append(table)
    
    # Build PDF
    doc.build(elements)
    output.seek(0)
    return output


@login_required
def export_report(request, report_type, export_format):
    """Export report in specified format."""
    # Determine which report view to use based on user role
    user_role = get_user_role(request.user)
    
    if user_role == UserProfile.ROLE_STAFF:
        report_view = StaffReportView()
    elif user_role == UserProfile.ROLE_LANDLORD:
        report_view = LandlordReportView()
    else:
        return HttpResponse('Unauthorized', status=403)
    
    # Set request and kwargs on the view instance
    report_view.request = request
    report_view.kwargs = {'report_type': report_type}
    
    # Get the report data
    report_key = report_view.get_report_key()
    if report_key != 'financial':
        return HttpResponse('Export only available for financial reports', status=400)
    
    scoped_data = report_view.get_base_queryset_data()
    report_context = report_view.build_report_context(report_key, scoped_data)
    
    # Build complete report data
    report_data = {
        'report_title': 'Financial Report',
        'report_headers': report_context.get('report_headers', []),
        'report_rows': report_context.get('report_rows', []),
        'report_summary_cards': report_context.get('report_summary_cards', []),
        'financial_active_filters': report_context.get('financial_active_filters', []),
    }
    
    if export_format == 'excel':
        output = export_financial_report_to_excel(report_data)
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="financial_report.xlsx"'
    elif export_format == 'pdf':
        output = export_financial_report_to_pdf(report_data)
        response = HttpResponse(output.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="financial_report.pdf"'
    else:
        return HttpResponse('Invalid export format', status=400)
    
    return response


@login_required
@require_POST
def mark_notifications_seen(request):
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON payload.'}, status=400)

    notification_keys = payload.get('notification_keys', [])
    if not isinstance(notification_keys, list):
        return JsonResponse({'ok': False, 'error': 'notification_keys must be a list.'}, status=400)

    cleaned_keys = []
    for key in notification_keys[:100]:
        if isinstance(key, str) and key.strip():
            cleaned_keys.append(key.strip()[:255])

    NotificationSeen.objects.bulk_create(
        [
            NotificationSeen(user=request.user, notification_key=key)
            for key in cleaned_keys
        ],
        ignore_conflicts=True,
    )
    return JsonResponse({'ok': True, 'seen_count': len(cleaned_keys)})
