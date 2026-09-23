from allauth.account.models import EmailAddress
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import TemplateView
from django.views.generic import UpdateView
from django.views.generic.edit import FormView

from .adapter import get_dashboard_url_for_user, get_user_role
from .forms import (
    ResendVerificationEmailForm,
    StaffLandlordForm,
    StaffLandlordPropertyFormSet,
    StaffPaymentForm,
    StaffPropertyForm,
    StaffTenantForm,
)
from .models import StaffProfile, UserProfile
from apps.payments.models import Payment
from apps.properties.models import Landlord, Property
from apps.tenants.models import Tenant


def build_detail_field(label, value):
    return {'label': label, 'value': value if value not in (None, '') else 'Not provided'}


class ResendVerificationEmailView(FormView):
    form_class = ResendVerificationEmailForm

    def form_valid(self, form):
        email = form.cleaned_data['email']
        email_address = (
            EmailAddress.objects.select_related('user')
            .filter(email__iexact=email, verified=False)
            .first()
        )

        if email_address:
            email_address.send_confirmation(self.request, signup=False)

        messages.success(
            self.request,
            'If this email is registered and still unverified, a new verification email has been sent.',
        )
        return redirect(reverse('account_email_verification_sent'))


class StaffOnlyMixin(LoginRequiredMixin):
    login_url = 'account_login'

    def dispatch(self, request, *args, **kwargs):
        if get_user_role(request.user) != UserProfile.ROLE_STAFF:
            return redirect(get_dashboard_url_for_user(request.user))
        return super().dispatch(request, *args, **kwargs)

    def get_staff_profile(self):
        staff_profile, _ = StaffProfile.objects.get_or_create(user=self.request.user)
        return staff_profile


class LandlordOnlyMixin(LoginRequiredMixin):
    login_url = 'account_login'

    def dispatch(self, request, *args, **kwargs):
        if get_user_role(request.user) != UserProfile.ROLE_LANDLORD:
            return redirect(get_dashboard_url_for_user(request.user))
        return super().dispatch(request, *args, **kwargs)

    def get_landlord_profile(self):
        return getattr(self.request.user, 'landlord_profile', None)


class StaffLandlordCreateView(StaffOnlyMixin, CreateView):
    form_class = StaffLandlordForm
    template_name = 'accounts/staff_landlord_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['staff_profile'] = self.get_staff_profile()
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Landlord created and assigned to you successfully.')
        return response

    def get_success_url(self):
        return reverse('accounts:staff-landlord-create')


class StaffLandlordUpdateView(StaffOnlyMixin, UpdateView):
    model = Landlord
    form_class = StaffLandlordForm
    template_name = 'accounts/staff_landlord_form.html'

    def get_queryset(self):
        return self.get_staff_profile().landlords.all()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['staff_profile'] = self.get_staff_profile()
        return kwargs

    def get_property_formset(self):
        kwargs = {
            'instance': self.object,
            'queryset': self.object.managed_properties.order_by('property_name'),
        }
        if self.request.method in ('POST', 'PUT'):
            kwargs['data'] = self.request.POST
        return StaffLandlordPropertyFormSet(**kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault('property_formset', self.get_property_formset())
        return context

    def form_valid(self, form):
        property_formset = self.get_property_formset()
        if not property_formset.is_valid():
            return self.form_invalid(form)

        with transaction.atomic():
            response = super().form_valid(form)
            property_formset.instance = self.object
            property_formset.save()
        messages.success(self.request, 'Landlord updated successfully.')
        return response

    def form_invalid(self, form):
        return self.render_to_response(
            self.get_context_data(form=form, property_formset=self.get_property_formset())
        )

    def get_success_url(self):
        return reverse('accounts:staff-landlord-list')


class StaffLandlordListView(StaffOnlyMixin, TemplateView):
    template_name = 'accounts/staff_landlord_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        landlords = self.get_staff_profile().landlords.select_related('user').prefetch_related(
            'managed_properties'
        )
        landlord_rows = []

        for landlord in landlords:
            properties = list(landlord.managed_properties.all())
            if properties:
                for property in properties:
                    landlord_rows.append(
                        {
                            'landlord': landlord,
                            'property_name': property.property_name,
                            'property_type': property.property_type,
                            'property_address': property.address,
                            'number_of_units': property.number_of_units,
                        }
                    )
            else:
                landlord_rows.append(
                    {
                        'landlord': landlord,
                        'property_name': 'Not assigned',
                        'property_type': 'Not assigned',
                        'property_address': 'Not assigned',
                        'number_of_units': 0,
                    }
                )

        context.update(
            {
                'managed_landlords': landlord_rows,
                'managed_landlords_count': len(landlord_rows),
            }
        )
        return context


class StaffLandlordDetailView(StaffOnlyMixin, TemplateView):
    template_name = 'accounts/record_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        landlord = get_object_or_404(
            self.get_staff_profile().landlords.select_related('user').prefetch_related(
                'managed_properties__tenants'
            ),
            pk=self.kwargs['pk'],
        )
        properties = list(landlord.managed_properties.all())
        property_names = ', '.join(property.property_name for property in properties) or 'Not assigned'

        context.update(
            {
                'base_template': 'dashboard/staff_base.html',
                'page_title': f'{landlord.user.username or landlord.user.email} - Landlord Record',
                'page_heading': landlord.user.username or landlord.user.email,
                'page_intro': 'Full landlord profile and linked property information.',
                'back_url': reverse('accounts:staff-landlord-list'),
                'back_label': 'Back to landlord list',
                'summary_cards': [
                    {'label': 'Properties', 'value': len(properties)},
                    {'label': 'Commission', 'value': f'{landlord.commission_percentage}%'},
                    {
                        'label': 'Tenant Count',
                        'value': sum(property.tenants.count() for property in properties),
                    },
                ],
                'detail_sections': [
                    {
                        'title': 'Landlord Information',
                        'fields': [
                            build_detail_field('Username', landlord.user.username or landlord.user.email),
                            build_detail_field('Email', landlord.email or landlord.user.email),
                            build_detail_field('Phone Number', landlord.phone_number),
                            build_detail_field('Address', landlord.address),
                            build_detail_field('Notes', landlord.notes),
                            build_detail_field('Commission Percentage', f'{landlord.commission_percentage}%'),
                            build_detail_field('Created At', landlord.created_at),
                            build_detail_field('Updated At', landlord.updated_at),
                        ],
                    },
                    {
                        'title': 'Property Overview',
                        'fields': [
                            build_detail_field('Assigned Properties', property_names),
                            build_detail_field('Property Count', len(properties)),
                        ],
                    },
                ],
            }
        )
        return context


class StaffTenantCreateView(StaffOnlyMixin, CreateView):
    form_class = StaffTenantForm
    template_name = 'accounts/staff_tenant_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['staff_profile'] = self.get_staff_profile()
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Tenant created and assigned to you successfully.')
        return response

    def get_success_url(self):
        return reverse('accounts:staff-tenant-create')


class StaffTenantListView(StaffOnlyMixin, TemplateView):
    template_name = 'accounts/staff_tenant_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        staff_profile = self.get_staff_profile()
        landlords = staff_profile.landlords.select_related('user').all()
        tenants = staff_profile.tenants.select_related(
            'landlord',
            'landlord__user',
            'property',
        )
        selected_landlord_id = self.request.GET.get('landlord')
        selected_property_id = self.request.GET.get('property')

        if selected_landlord_id:
            tenants = tenants.filter(landlord_id=selected_landlord_id)

        if selected_property_id:
            tenants = tenants.filter(property_id=selected_property_id)

        selected_landlord = None
        if selected_landlord_id and landlords.filter(pk=selected_landlord_id).exists():
            selected_landlord = landlords.filter(pk=selected_landlord_id).first()

        # Get property options
        properties = (
            Property.objects.filter(landlord__in=landlords)
            .select_related('landlord', 'landlord__user')
            .order_by('property_name')
        )

        tenants = list(tenants)
        for tenant in tenants:
            tenant.property_name_display = tenant.property.property_name if tenant.property_id else ''

        context.update(
            {
                'managed_tenants': tenants,
                'managed_tenants_count': len(tenants),
                'landlord_options': landlords,
                'property_options': properties,
                'selected_landlord_id': selected_landlord_id or '',
                'selected_property_id': selected_property_id or '',
                'selected_landlord': selected_landlord,
            }
        )
        return context


class StaffTenantDetailView(StaffOnlyMixin, TemplateView):
    template_name = 'accounts/record_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = get_object_or_404(
            self.get_staff_profile().tenants.select_related(
                'landlord',
                'landlord__user',
                'property',
            ).prefetch_related('payments'),
            pk=self.kwargs['pk'],
        )

        context.update(
            {
                'base_template': 'dashboard/staff_base.html',
                'page_title': f'{tenant.name} - Tenant Record',
                'page_heading': tenant.name,
                'page_intro': 'Full tenant record, tenancy details, and payment setup.',
                'back_url': reverse('accounts:staff-tenant-list'),
                'back_label': 'Back to tenant list',
                'summary_cards': [
                    {'label': 'Tenancy Type', 'value': tenant.get_tenancy_type_display()},
                    {'label': 'Payment Amount', 'value': tenant.payment_amount},
                    {'label': 'Payment Records', 'value': tenant.payments.count()},
                ],
                'detail_sections': [
                    {
                        'title': 'Tenant Information',
                        'fields': [
                            build_detail_field('Name', tenant.name),
                            build_detail_field('Phone Number', tenant.phone_number),
                            build_detail_field('Email', tenant.email),
                            build_detail_field('Address', tenant.address),
                            build_detail_field('Apartment Type', tenant.apartment_type),
                            build_detail_field('Tenancy Type', tenant.get_tenancy_type_display()),
                            build_detail_field('Payment Mode', tenant.get_payment_mode_display()),
                            build_detail_field('Payment Amount', tenant.payment_amount),
                        ],
                    },
                    {
                        'title': 'Assignment Details',
                        'fields': [
                            build_detail_field('Landlord', tenant.landlord_name),
                            build_detail_field(
                                'Property',
                                tenant.property.property_name if tenant.property_id else 'Not assigned',
                            ),
                            build_detail_field('Created At', tenant.created_at),
                            build_detail_field('Updated At', tenant.updated_at),
                        ],
                    },
                ],
            }
        )
        return context


class LandlordTenantListView(LandlordOnlyMixin, TemplateView):
    template_name = 'accounts/landlord_tenant_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        landlord = self.get_landlord_profile()
        selected_property_id = self.request.GET.get('property')

        if landlord is None:
            properties = Property.objects.none()
            tenants = Tenant.objects.none()
        else:
            properties = (
                Property.objects.filter(landlord=landlord)
                .select_related('landlord', 'landlord__user')
                .order_by('property_name')
            )
            tenants = (
                Tenant.objects.filter(landlord=landlord)
                .select_related('landlord', 'landlord__user', 'property')
                .order_by('name')
            )

        if selected_property_id and properties.filter(pk=selected_property_id).exists():
            tenants = tenants.filter(property_id=selected_property_id)

        tenants = list(tenants)
        for tenant in tenants:
            tenant.property_name_display = tenant.property.property_name if tenant.property_id else 'Not assigned'

        context.update(
            {
                'managed_tenants': tenants,
                'managed_tenants_count': len(tenants),
                'property_options': properties,
                'selected_property_id': selected_property_id or '',
            }
        )
        return context


class LandlordTenantDetailView(LandlordOnlyMixin, TemplateView):
    template_name = 'accounts/record_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        landlord = self.get_landlord_profile()
        tenant = get_object_or_404(
            Tenant.objects.select_related('landlord', 'landlord__user', 'property').prefetch_related('payments'),
            pk=self.kwargs['pk'],
            landlord=landlord,
        )

        context.update(
            {
                'base_template': 'dashboard/landlord_base.html',
                'page_title': f'{tenant.name} - Tenant Record',
                'page_heading': tenant.name,
                'page_intro': 'Full tenant profile for your property portfolio.',
                'back_url': reverse('accounts:landlord-tenant-list'),
                'back_label': 'Back to tenant list',
                'summary_cards': [
                    {'label': 'Property', 'value': tenant.property.property_name if tenant.property_id else 'Not assigned'},
                    {'label': 'Tenancy Type', 'value': tenant.get_tenancy_type_display()},
                    {'label': 'Payment Amount', 'value': tenant.payment_amount},
                ],
                'detail_sections': [
                    {
                        'title': 'Tenant Information',
                        'fields': [
                            build_detail_field('Name', tenant.name),
                            build_detail_field('Phone Number', tenant.phone_number),
                            build_detail_field('Email', tenant.email),
                            build_detail_field('Address', tenant.address),
                            build_detail_field('Apartment Type', tenant.apartment_type),
                            build_detail_field('Tenancy Type', tenant.get_tenancy_type_display()),
                            build_detail_field('Payment Mode', tenant.get_payment_mode_display()),
                            build_detail_field('Payment Amount', tenant.payment_amount),
                        ],
                    },
                    {
                        'title': 'Assignment Details',
                        'fields': [
                            build_detail_field(
                                'Property',
                                tenant.property.property_name if tenant.property_id else 'Not assigned',
                            ),
                            build_detail_field('Landlord', tenant.landlord_name),
                            build_detail_field('Created At', tenant.created_at),
                            build_detail_field('Updated At', tenant.updated_at),
                        ],
                    },
                ],
            }
        )
        return context


class LandlordPropertyListView(LandlordOnlyMixin, TemplateView):
    template_name = 'accounts/landlord_property_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        landlord = self.get_landlord_profile()

        if landlord is None:
            properties = []
        else:
            properties = list(
                Property.objects.filter(landlord=landlord)
                .select_related('landlord', 'landlord__user')
                .prefetch_related('tenants')
                .order_by('property_name')
            )

        for property_obj in properties:
            property_obj.occupied_units_count = property_obj.tenants.count()

        context.update(
            {
                'managed_properties': properties,
                'managed_properties_count': len(properties),
            }
        )
        return context


class StaffTenantUpdateView(StaffOnlyMixin, UpdateView):
    model = Tenant
    form_class = StaffTenantForm
    template_name = 'accounts/staff_tenant_form.html'

    def get_queryset(self):
        staff_profile = self.get_staff_profile()
        return staff_profile.tenants.all()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['staff_profile'] = self.get_staff_profile()
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Tenant updated successfully.')
        return response

    def get_success_url(self):
        return reverse('accounts:staff-tenant-list')


class StaffPropertyCreateView(StaffOnlyMixin, CreateView):
    form_class = StaffPropertyForm
    template_name = 'accounts/staff_property_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['staff_profile'] = self.get_staff_profile()
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Property created successfully.')
        return response

    def get_success_url(self):
        return reverse('accounts:staff-property-create')


class StaffPaymentCreateView(StaffOnlyMixin, CreateView):
    form_class = StaffPaymentForm
    template_name = 'accounts/staff_payment_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['staff_profile'] = self.get_staff_profile()
        kwargs['recorded_by'] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Payment recorded successfully.')
        return response

    def get_success_url(self):
        return reverse('accounts:staff-payment-create')


class StaffPaymentUpdateView(StaffOnlyMixin, UpdateView):
    model = Payment
    form_class = StaffPaymentForm
    template_name = 'accounts/staff_payment_form.html'

    def get_queryset(self):
        staff_profile = self.get_staff_profile()
        landlords = staff_profile.landlords.all()
        return (
            Payment.objects.filter(
                Q(tenant__in=staff_profile.tenants.all()) |
                Q(property__landlord__in=landlords)
            )
            .distinct()
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['staff_profile'] = self.get_staff_profile()
        kwargs['recorded_by'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment = self.object
        context.update(
            {
                'form_mode': 'edit',
                'form_title': 'Edit Payment',
                'form_intro': f'Update the payment record for {payment.tenant_name}.',
            }
        )
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Payment updated successfully.')
        return response

    def get_success_url(self):
        return reverse('accounts:staff-payment-list')


class StaffPaymentListView(StaffOnlyMixin, TemplateView):
    template_name = 'accounts/staff_payment_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        staff_profile = self.get_staff_profile()
        landlords = staff_profile.landlords.select_related('user').all()
        selected_landlord_id = self.request.GET.get('landlord')
        selected_property_id = self.request.GET.get('property')
        selected_start_date = self.request.GET.get('start_date', '').strip()
        selected_end_date = self.request.GET.get('end_date', '').strip()
        payments = (
            Payment.objects.select_related('tenant', 'property', 'recorded_by', 'property__landlord', 'property__landlord__user')
            .filter(
                Q(tenant__in=staff_profile.tenants.all()) |
                Q(property__landlord__in=landlords)
            )
            .distinct()
            .order_by('-due_date', '-created_at')
        )

        property_options = (
            Property.objects.select_related('landlord', 'landlord__user')
            .filter(landlord__in=landlords)
            .order_by('property_name')
        )

        if selected_landlord_id and landlords.filter(pk=selected_landlord_id).exists():
            payments = payments.filter(property__landlord_id=selected_landlord_id)
            property_options = property_options.filter(landlord_id=selected_landlord_id)

        if selected_property_id and property_options.filter(pk=selected_property_id).exists():
            payments = payments.filter(property_id=selected_property_id)

        if selected_start_date:
            try:
                payments = payments.filter(due_date__gte=date.fromisoformat(selected_start_date))
            except ValueError:
                selected_start_date = ''

        if selected_end_date:
            try:
                payments = payments.filter(due_date__lte=date.fromisoformat(selected_end_date))
            except ValueError:
                selected_end_date = ''

        context.update(
            {
                'managed_payments': payments,
                'managed_payments_count': payments.count(),
                'landlord_options': landlords,
                'property_options': property_options,
                'selected_landlord_id': selected_landlord_id or '',
                'selected_property_id': selected_property_id or '',
                'selected_start_date': selected_start_date,
                'selected_end_date': selected_end_date,
            }
        )
        return context


class StaffPaymentDetailView(StaffOnlyMixin, TemplateView):
    template_name = 'accounts/record_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        staff_profile = self.get_staff_profile()
        landlords = staff_profile.landlords.all()
        payment = get_object_or_404(
            Payment.objects.select_related(
                'tenant',
                'property',
                'recorded_by',
                'property__landlord',
                'property__landlord__user',
            )
            .filter(
                Q(tenant__in=staff_profile.tenants.all()) |
                Q(property__landlord__in=landlords)
            )
            .distinct(),
            pk=self.kwargs['pk'],
        )

        context.update(
            {
                'base_template': 'dashboard/staff_base.html',
                'page_title': f'Payment #{payment.pk}',
                'page_heading': f'Payment Record #{payment.pk}',
                'page_intro': 'Full payment details for this managed rent record.',
                'back_url': reverse('accounts:staff-payment-list'),
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
