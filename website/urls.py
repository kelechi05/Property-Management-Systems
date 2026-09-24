"""
URL configuration for the website app.
"""
from django.urls import path
from . import views

app_name = 'website'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('services/', views.ServicesView.as_view(), name='services'),
    path('services/<int:pk>/', views.ServicesView.as_view(), name='service-detail'),
    path('properties/', views.PropertiesView.as_view(), name='properties'),
    path('properties/<int:pk>/', views.PropertyDetailView.as_view(), name='property-detail'),
    path('contact/', views.ContactView.as_view(), name='contact'),
]
