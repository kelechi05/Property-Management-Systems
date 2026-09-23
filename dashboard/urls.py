"""
URL configuration for the dashboard app.
"""
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardIndexView.as_view(), name='index'),
    path('notifications/mark-seen/', views.mark_notifications_seen, name='notifications_mark_seen'),
    path('pending-approval/', views.PendingApprovalView.as_view(), name='pending_approval'),
    path('user/', views.UserDashboardView.as_view(), name='user'),
    path('staff/', views.StaffDashboardView.as_view(), name='staff'),
    path('staff/reports/<str:report_type>/', views.StaffReportView.as_view(), name='staff-report'),
    path('staff/reports/<str:report_type>/export/<str:export_format>/', views.export_report, name='staff-report-export'),
    path('landlord/', views.LandlordDashboardView.as_view(), name='landlord'),
    path('landlord/payments/', views.LandlordPaymentReportView.as_view(), name='landlord-payments'),
    path('landlord/payments/<int:pk>/', views.LandlordPaymentDetailView.as_view(), name='landlord-payment-detail'),
    path('landlord/reports/<str:report_type>/', views.LandlordReportView.as_view(), name='landlord-report'),
    path('landlord/reports/<str:report_type>/export/<str:export_format>/', views.export_report, name='landlord-report-export'),
    path('tenant/', views.TenantDashboardView.as_view(), name='tenant'),
    path('tenant/payments/', views.TenantPaymentReportView.as_view(), name='tenant-payments'),
    path('tenant/payments/<int:pk>/', views.TenantPaymentDetailView.as_view(), name='tenant-payment-detail'),
]
