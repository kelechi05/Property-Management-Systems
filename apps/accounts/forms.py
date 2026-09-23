from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError

from apps.payments.models import Payment
from apps.properties.models import Landlord, Property
from apps.tenants.models import Tenant

from .models import UserProfile
from .utils import to_proper_case


class CustomSignupForm(forms.Form):
    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        return to_proper_case(username)

    def signup(self, request, user):
        UserProfile.objects.update_or_create(
            user=user,
            defaults={'role': UserProfile.ROLE_USER},
        )


class ResendVerificationEmailForm(forms.Form):
    email = forms.EmailField()


class StaffLandlordForm(forms.ModelForm):
    class Meta:
        model = Landlord
        fields = (
            'user',
            'email',
            'phone_number',
            'address',
            'commission_percentage',
            'notes',
        )
        widgets = {
            'address': forms.Textarea(attrs={'rows': 4}),
            'notes': forms.Textarea(attrs={'rows': 4}),
            'commission_percentage': forms.NumberInput(attrs={
                'min': 0,
                'max': 100,
                'step': 0.01,
                'placeholder': 'Enter commission percentage (0-100)',
            }),
        }

    def __init__(self, *args, staff_profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.staff_profile = staff_profile

    def save(self, commit=True):
        landlord = super().save(commit=commit)
        if commit and self.staff_profile is not None:
            self.staff_profile.landlords.add(landlord)
        return landlord


StaffLandlordPropertyFormSet = inlineformset_factory(
    Landlord,
    Property,
    fields=(
        'property_name',
        'property_type',
        'number_of_units',
        'address',
        'city',
        'state',
        'description',
    ),
    extra=0,
    can_delete=False,
    widgets={
        'address': forms.Textarea(attrs={'rows': 3}),
        'description': forms.Textarea(attrs={'rows': 3}),
    },
)


class StaffTenantForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = (
            'name',
            'phone_number',
            'apartment_type',
            'tenancy_type',
            'payment_mode',
            'address',
            'email',
            'landlord',
            'property',
            'landlord_name',
            'payment_amount',
        )
        widgets = {
            'address': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, staff_profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.staff_profile = staff_profile

        if staff_profile is not None:
            self.fields['landlord'].queryset = staff_profile.landlords.all()
            self.fields['property'].queryset = (
                Property.objects.filter(landlord__in=staff_profile.landlords.all())
                .select_related('landlord', 'landlord__user')
                .order_by('property_name')
            )
        else:
            self.fields['property'].queryset = Property.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        landlord = cleaned_data.get('landlord')
        property_obj = cleaned_data.get('property')

        if landlord and self.staff_profile is not None:
            if not self.staff_profile.landlords.filter(pk=landlord.pk).exists():
                self.add_error('landlord', 'You can only assign tenants to landlords managed by this staff member.')

        if property_obj and self.staff_profile is not None:
            if not self.staff_profile.landlords.filter(pk=property_obj.landlord_id).exists():
                self.add_error('property', 'You can only assign tenants to properties managed by this staff member.')

        if property_obj and landlord and property_obj.landlord_id != landlord.pk:
            self.add_error('property', 'The selected property must belong to the selected landlord.')

        if property_obj and not landlord:
            cleaned_data['landlord'] = property_obj.landlord

        return cleaned_data

    def save(self, commit=True):
        tenant = super().save(commit=commit)
        if commit and self.staff_profile is not None:
            self.staff_profile.tenants.add(tenant)
        return tenant


class StaffPropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = (
            'landlord',
            'property_name',
            'property_type',
            'number_of_units',
            'address',
            'city',
            'state',
            'description',
        )
        widgets = {
            'address': forms.Textarea(attrs={'rows': 4}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, staff_profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.staff_profile = staff_profile

        if staff_profile is not None:
            self.fields['landlord'].queryset = staff_profile.landlords.all()

    def clean(self):
        cleaned_data = super().clean()
        landlord = cleaned_data.get('landlord')

        if landlord and self.staff_profile is not None:
            if not self.staff_profile.landlords.filter(pk=landlord.pk).exists():
                self.add_error('landlord', 'You can only create properties for landlords managed by this staff member.')

        return cleaned_data


class StaffPaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = (
            'tenant',
            'property',
            'amount_to_pay',
            'payment_date',
            'due_date',
            'payment_method',
            'status',
            'bank_reference',
            'rent_period_start',
            'rent_period_end',
        )
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'rent_period_start': forms.DateInput(attrs={'type': 'date'}),
            'rent_period_end': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, staff_profile=None, recorded_by=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.staff_profile = staff_profile
        self.recorded_by = recorded_by

        if staff_profile is not None:
            self.fields['tenant'].queryset = (
                staff_profile.tenants.select_related('landlord', 'landlord__user').all()
            )
            self.fields['property'].queryset = (
                Property.objects.filter(landlord__in=staff_profile.landlords.all())
                .select_related('landlord', 'landlord__user')
                .distinct()
            )

    def clean(self):
        cleaned_data = super().clean()
        tenant = cleaned_data.get('tenant')
        property_obj = cleaned_data.get('property')

        if tenant and self.staff_profile is not None:
            if not self.staff_profile.tenants.filter(pk=tenant.pk).exists():
                self.add_error('tenant', 'You can only record payments for tenants managed by this staff member.')

        if property_obj and self.staff_profile is not None:
            if not self.staff_profile.landlords.filter(pk=property_obj.landlord_id).exists():
                self.add_error('property', 'You can only record payments for properties owned by your assigned landlords.')

        if tenant and property_obj and tenant.landlord_id and property_obj.landlord_id:
            if tenant.landlord_id != property_obj.landlord_id:
                raise ValidationError('The selected tenant and property must belong to the same landlord.')

        if tenant and tenant.property_id and property_obj and tenant.property_id != property_obj.pk:
            self.add_error('property', 'This tenant is assigned to a different property.')

        return cleaned_data

    def save(self, commit=True):
        payment = super().save(commit=False)

        if payment.tenant:
            payment.tenant_name = payment.tenant.name
            if not payment.amount_to_pay:
                payment.amount_to_pay = payment.tenant.payment_amount

        if payment.property:
            payment.property_name = payment.property.property_name

        if payment.status == Payment.STATUS_REMITTED:
            payment.amount_paid = payment.amount_to_pay or 0
        else:
            payment.amount_paid = 0
            payment.payment_date = None

        if self.recorded_by is not None:
            payment.recorded_by = self.recorded_by

        if commit:
            payment.save()

        return payment
