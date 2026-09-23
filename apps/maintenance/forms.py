from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import StaffProfile
from apps.properties.models import Property
from apps.tenants.models import Tenant

from .models import MaintenanceReport

User = get_user_model()


class TenantMaintenanceReportForm(forms.ModelForm):
    class Meta:
        model = MaintenanceReport
        fields = ('property', 'description', 'priority')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.tenant_record = None

        if user is not None:
            self.tenant_record = (
                Tenant.objects.select_related('landlord', 'landlord__user')
                .filter(email__iexact=user.email)
                .first()
            )

        if self.tenant_record and self.tenant_record.landlord_id:
            queryset = Property.objects.filter(
                landlord=self.tenant_record.landlord
            ).order_by('property_name')
            self.fields['property'].queryset = queryset
            self.fields['property'].required = False
        else:
            self.fields['property'].queryset = Property.objects.none()
            self.fields['property'].required = False

    def clean(self):
        cleaned_data = super().clean()
        property_obj = cleaned_data.get('property')

        if self.tenant_record is None:
            raise ValidationError('Your tenant profile could not be found for this account.')

        if self.tenant_record.landlord_id is None:
            raise ValidationError('Your tenant record is not assigned to a landlord yet.')

        if property_obj and property_obj.landlord_id != self.tenant_record.landlord_id:
            self.add_error('property', 'You can only report maintenance for your landlord properties.')

        # Set related objects before model validation runs so the model does not
        # raise errors for fields that are not exposed on this form.
        self.instance.tenant = self.tenant_record
        self.instance.landlord = self.tenant_record.landlord
        self.instance.created_by = self.user
        self.instance.submitted_by = MaintenanceReport.SUBMITTED_BY_TENANT

        return cleaned_data

    def save(self, commit=True):
        report = super().save(commit=False)
        report.tenant = self.tenant_record
        report.landlord = self.tenant_record.landlord
        report.created_by = self.user
        report.submitted_by = MaintenanceReport.SUBMITTED_BY_TENANT

        if commit:
            report.save()

        return report


class StaffMaintenanceReportForm(forms.ModelForm):
    class Meta:
        model = MaintenanceReport
        fields = (
            'tenant',
            'property',
            'description',
            'priority',
            'status',
            'cost',
            'staff_note',
            'assigned_staff',
        )
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'staff_note': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, staff_profile=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.staff_profile = staff_profile
        self.user = user

        self.fields['cost'].required = False
        self.fields['tenant'].required = False
        self.fields['property'].required = False
        self.fields['assigned_staff'].required = False

        if staff_profile is not None:
            landlords = staff_profile.landlords.all()
            self.fields['tenant'].queryset = (
                staff_profile.tenants.select_related('landlord', 'landlord__user').all()
            )
            self.fields['property'].queryset = (
                Property.objects.filter(landlord__in=landlords)
                .select_related('landlord', 'landlord__user')
                .distinct()
                .order_by('property_name')
            )
            staff_users = [staff_profile.user]
            for profile in StaffProfile.objects.filter(
                landlords__in=landlords,
                is_active=True,
            ).select_related('user').distinct():
                staff_users.append(profile.user)
            seen_user_ids = set()
            unique_users = []
            for staff_user in staff_users:
                if staff_user.pk not in seen_user_ids:
                    seen_user_ids.add(staff_user.pk)
                    unique_users.append(staff_user.pk)
            self.fields['assigned_staff'].queryset = User.objects.filter(pk__in=unique_users)
            self.fields['assigned_staff'].initial = user
        else:
            self.fields['tenant'].queryset = Tenant.objects.none()
            self.fields['property'].queryset = Property.objects.none()
            self.fields['assigned_staff'].queryset = User.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        tenant = cleaned_data.get('tenant')
        property_obj = cleaned_data.get('property')
        assigned_staff = cleaned_data.get('assigned_staff')

        if not tenant and not property_obj:
            raise ValidationError('Select at least a tenant or a property for the maintenance report.')

        landlord = None
        if tenant:
            landlord = tenant.landlord
            if self.staff_profile is not None and not self.staff_profile.tenants.filter(pk=tenant.pk).exists():
                self.add_error('tenant', 'You can only log maintenance for tenants assigned to you.')

        if property_obj:
            landlord = property_obj.landlord if landlord is None else landlord
            if self.staff_profile is not None and not self.staff_profile.landlords.filter(pk=property_obj.landlord_id).exists():
                self.add_error('property', 'You can only log maintenance for properties owned by your assigned landlords.')

        if tenant and property_obj and tenant.landlord_id and property_obj.landlord_id:
            if tenant.landlord_id != property_obj.landlord_id:
                raise ValidationError('The selected tenant and property must belong to the same landlord.')

        if tenant and tenant.property_id and property_obj and tenant.property_id != property_obj.pk:
            self.add_error('property', 'This tenant is assigned to a different property.')

        if assigned_staff and self.staff_profile is not None:
            allowed_staff_ids = set(
                StaffProfile.objects.filter(
                    landlords__in=self.staff_profile.landlords.all(),
                    is_active=True,
                ).values_list('user_id', flat=True)
            )
            allowed_staff_ids.add(self.staff_profile.user_id)
            if assigned_staff.pk not in allowed_staff_ids:
                self.add_error('assigned_staff', 'You can only assign this report to staff connected to the same landlords.')

        self.landlord = landlord
        return cleaned_data

    def save(self, commit=True):
        report = super().save(commit=False)
        report.landlord = self.landlord
        report.created_by = self.user
        report.submitted_by = MaintenanceReport.SUBMITTED_BY_STAFF

        if report.status in {MaintenanceReport.STATUS_RESOLVED, MaintenanceReport.STATUS_CLOSED}:
            report.resolved_at = report.resolved_at or timezone.now()
        elif report.status in {MaintenanceReport.STATUS_NEW, MaintenanceReport.STATUS_IN_PROGRESS}:
            report.resolved_at = None

        if commit:
            report.save()

        return report


class StaffMaintenanceStatusForm(forms.ModelForm):
    class Meta:
        model = MaintenanceReport
        fields = ('status', 'priority', 'cost', 'staff_note', 'assigned_staff')
        widgets = {
            'staff_note': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, staff_profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.staff_profile = staff_profile

        if staff_profile is not None:
            staff_users = [staff_profile.user]
            for profile in StaffProfile.objects.filter(
                landlords__in=staff_profile.landlords.all(),
                is_active=True,
            ).select_related('user').distinct():
                staff_users.append(profile.user)
            seen_user_ids = set()
            unique_user_ids = []
            for staff_user in staff_users:
                if staff_user.pk not in seen_user_ids:
                    seen_user_ids.add(staff_user.pk)
                    unique_user_ids.append(staff_user.pk)
            self.fields['assigned_staff'].queryset = User.objects.filter(pk__in=unique_user_ids)

    def save(self, commit=True):
        report = super().save(commit=False)
        if report.status in {MaintenanceReport.STATUS_RESOLVED, MaintenanceReport.STATUS_CLOSED}:
            report.resolved_at = report.resolved_at or timezone.now()
        else:
            report.resolved_at = None

        if commit:
            report.save()

        return report
