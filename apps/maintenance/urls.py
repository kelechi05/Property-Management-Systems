from django.urls import path

from . import views

app_name = 'maintenance'

urlpatterns = [
    path('tenant/create/', views.TenantMaintenanceCreateView.as_view(), name='tenant-create'),
    path('tenant/', views.TenantMaintenanceListView.as_view(), name='tenant-list'),
    path('staff/create/', views.StaffMaintenanceCreateView.as_view(), name='staff-create'),
    path('staff/', views.StaffMaintenanceListView.as_view(), name='staff-list'),
    path('staff/<int:pk>/status/', views.StaffMaintenanceUpdateView.as_view(), name='staff-update'),
    path('landlord/', views.LandlordMaintenanceListView.as_view(), name='landlord-list'),
]
