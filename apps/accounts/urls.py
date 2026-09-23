from django.urls import path

from .views import (
    LandlordPropertyListView,
    LandlordTenantDetailView,
    ResendVerificationEmailView,
    LandlordTenantListView,
    StaffLandlordCreateView,
    StaffLandlordDetailView,
    StaffLandlordListView,
    StaffLandlordUpdateView,
    StaffPaymentCreateView,
    StaffPaymentDetailView,
    StaffPaymentListView,
    StaffPaymentUpdateView,
    StaffPropertyCreateView,
    StaffTenantCreateView,
    StaffTenantDetailView,
    StaffTenantListView,
    StaffTenantUpdateView,
)

app_name = 'accounts'

urlpatterns = [
    path('resend-verification/', ResendVerificationEmailView.as_view(), name='account_resend_verification'),
    path('staff/landlords/', StaffLandlordListView.as_view(), name='staff-landlord-list'),
    path('staff/landlords/add/', StaffLandlordCreateView.as_view(), name='staff-landlord-create'),
    path('staff/landlords/<int:pk>/', StaffLandlordDetailView.as_view(), name='staff-landlord-detail'),
    path('staff/landlords/<int:pk>/edit/', StaffLandlordUpdateView.as_view(), name='staff-landlord-update'),
    path('staff/payments/', StaffPaymentListView.as_view(), name='staff-payment-list'),
    path('staff/payments/add/', StaffPaymentCreateView.as_view(), name='staff-payment-create'),
    path('staff/payments/<int:pk>/', StaffPaymentDetailView.as_view(), name='staff-payment-detail'),
    path('staff/payments/<int:pk>/edit/', StaffPaymentUpdateView.as_view(), name='staff-payment-update'),
    path('staff/properties/add/', StaffPropertyCreateView.as_view(), name='staff-property-create'),
    path('staff/tenants/', StaffTenantListView.as_view(), name='staff-tenant-list'),
    path('staff/tenants/add/', StaffTenantCreateView.as_view(), name='staff-tenant-create'),
    path('staff/tenants/<int:pk>/', StaffTenantDetailView.as_view(), name='staff-tenant-detail'),
    path('staff/tenants/<int:pk>/edit/', StaffTenantUpdateView.as_view(), name='staff-tenant-update'),
    path('landlord/properties/', LandlordPropertyListView.as_view(), name='landlord-property-list'),
    path('landlord/tenants/', LandlordTenantListView.as_view(), name='landlord-tenant-list'),
    path('landlord/tenants/<int:pk>/', LandlordTenantDetailView.as_view(), name='landlord-tenant-detail'),
]
