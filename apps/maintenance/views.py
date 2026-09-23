from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, TemplateView, UpdateView

from apps.accounts.adapter import get_dashboard_url_for_user, get_user_role
from apps.accounts.models import StaffProfile, UserProfile
from apps.tenants.models import Tenant

from .forms import (
    StaffMaintenanceReportForm,
    StaffMaintenanceStatusForm,
    TenantMaintenanceReportForm,
)
from .models import MaintenanceReport


class MaintenanceRoleMixin(LoginRequiredMixin):
    login_url = 'account_login'
    allowed_roles = ()

    def dispatch(self, request, *args, **kwargs):
        if self.allowed_roles and get_user_role(request.user) not in self.allowed_roles:
            return redirect(get_dashboard_url_for_user(request.user))
        return super().dispatch(request, *args, **kwargs)


class StaffMaintenanceMixin(MaintenanceRoleMixin):
    allowed_roles = (UserProfile.ROLE_STAFF,)

    def get_staff_profile(self):
        staff_profile, _ = StaffProfile.objects.get_or_create(user=self.request.user)
        return staff_profile


class TenantMaintenanceCreateView(MaintenanceRoleMixin, CreateView):
    allowed_roles = (UserProfile.ROLE_TENANT,)
    form_class = TenantMaintenanceReportForm
    template_name = 'maintenance/tenant_report_form.html'
    success_url = reverse_lazy('maintenance:tenant-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Your maintenance complaint has been submitted successfully.')
        return response


class TenantMaintenanceListView(MaintenanceRoleMixin, TemplateView):
    allowed_roles = (UserProfile.ROLE_TENANT,)
    template_name = 'maintenance/tenant_report_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_record = Tenant.objects.filter(email__iexact=self.request.user.email).first()

        if tenant_record is None:
            reports = MaintenanceReport.objects.none()
        else:
            reports = (
                MaintenanceReport.objects.select_related('landlord__user', 'property', 'assigned_staff')
                .filter(tenant=tenant_record)
                .order_by('-created_at')
            )

        context.update(
            {
                'maintenance_reports': reports,
                'maintenance_reports_count': reports.count(),
            }
        )
        return context


class StaffMaintenanceCreateView(StaffMaintenanceMixin, CreateView):
    form_class = StaffMaintenanceReportForm
    template_name = 'maintenance/staff_report_form.html'
    success_url = reverse_lazy('maintenance:staff-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['staff_profile'] = self.get_staff_profile()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Maintenance report created successfully.')
        return response


class StaffMaintenanceListView(StaffMaintenanceMixin, TemplateView):
    template_name = 'maintenance/staff_report_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        staff_profile = self.get_staff_profile()
        status_filter = self.request.GET.get('status', '').strip()

        reports = (
            MaintenanceReport.objects.select_related('landlord__user', 'tenant', 'property', 'assigned_staff')
            .filter(
                Q(tenant__in=staff_profile.tenants.all()) |
                Q(landlord__in=staff_profile.landlords.all())
            )
            .distinct()
            .order_by('-created_at')
        )

        if status_filter:
            reports = reports.filter(status=status_filter)

        context.update(
            {
                'maintenance_reports': reports,
                'maintenance_reports_count': reports.count(),
                'status_choices': MaintenanceReport.STATUS_CHOICES,
                'selected_status': status_filter,
            }
        )
        return context


class StaffMaintenanceUpdateView(StaffMaintenanceMixin, UpdateView):
    model = MaintenanceReport
    form_class = StaffMaintenanceStatusForm
    template_name = 'maintenance/staff_status_form.html'
    success_url = reverse_lazy('maintenance:staff-list')

    def get_queryset(self):
        staff_profile = self.get_staff_profile()
        return (
            MaintenanceReport.objects.select_related('landlord__user', 'tenant', 'property', 'assigned_staff')
            .filter(
                Q(tenant__in=staff_profile.tenants.all()) |
                Q(landlord__in=staff_profile.landlords.all())
            )
            .distinct()
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['staff_profile'] = self.get_staff_profile()
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Maintenance status updated successfully.')
        return response


class LandlordMaintenanceListView(MaintenanceRoleMixin, TemplateView):
    allowed_roles = (UserProfile.ROLE_LANDLORD,)
    template_name = 'maintenance/landlord_report_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        landlord = getattr(self.request.user, 'landlord_profile', None)
        status_filter = self.request.GET.get('status', '').strip()

        if landlord is None:
            reports = MaintenanceReport.objects.none()
        else:
            reports = (
                MaintenanceReport.objects.select_related('tenant', 'property', 'assigned_staff')
                .filter(landlord=landlord)
                .order_by('-created_at')
            )

        if status_filter:
            reports = reports.filter(status=status_filter)

        context.update(
            {
                'maintenance_reports': reports,
                'maintenance_reports_count': reports.count(),
                'status_choices': MaintenanceReport.STATUS_CHOICES,
                'selected_status': status_filter,
            }
        )
        return context
