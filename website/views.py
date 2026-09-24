"""
Views for the public-facing website.
"""
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, ListView, TemplateView, FormView
from django.urls import reverse_lazy

from .models import HeroSection, Listing, MeetOurTeam, Service
from .forms import ContactForm


class HomeView(TemplateView):
    template_name = 'website/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hero_slides'] = (
            HeroSection.objects.filter(is_active=True).order_by('sort_order', '-created_at')
            or HeroSection.objects.order_by('sort_order', '-created_at')
        )
        context['services'] = Service.objects.filter(is_active=True)
        context['listings'] = Listing.objects.filter(is_checked=True)
        return context


class AboutView(TemplateView):
    template_name = 'website/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['team_members'] = MeetOurTeam.objects.all()
        return context


class ServicesView(TemplateView):
    template_name = 'website/services.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        services = Service.objects.filter(is_active=True)
        service_pk = self.kwargs.get('pk')
        active_service = (
            get_object_or_404(services, pk=service_pk)
            if service_pk is not None
            else services.first()
        )
        context['services'] = services
        context['active_service'] = active_service
        return context


class PropertiesView(ListView):
    template_name = 'website/properties.html'
    context_object_name = 'listings'

    def get_queryset(self):
        return Listing.objects.all().order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get the first active service to use its image for the hero background
        context['service'] = Service.objects.filter(is_active=True).first()
        return context
        
class PropertyDetailView(DetailView):
    template_name = 'website/property_detail.html'
    model = Listing
    context_object_name = 'listing'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        listing = context['listing']
        gallery_images = [listing.image]
        gallery_images.extend(
            image.image
            for image in listing.gallery_images.all()
            if image.image
        )
        context['gallery_images'] = gallery_images
        return context


class ContactView(FormView):
    template_name = 'website/contact.html'
    form_class = ContactForm
    success_url = reverse_lazy('website:contact')

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)
