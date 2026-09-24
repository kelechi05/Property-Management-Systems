"""
Models for the website app (testimonials, blog posts, etc.)
"""
from django.db import models
from django.core.validators import FileExtensionValidator

from apps.properties.models import Landlord


class HeroSection(models.Model):
    """Homepage hero content."""
    headline = models.CharField(max_length=140, help_text="Main H1 heading")
    blurb = models.TextField(help_text="Short supporting paragraph")
    background_image = models.FileField(
        upload_to='hero/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])],
        help_text="Background image for hero section",
    )
    sort_order = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first in the slider")
    is_active = models.BooleanField(default=True, help_text="Show this slide in the homepage slider")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', '-created_at']
        verbose_name = "Hero section"
        verbose_name_plural = "Hero sections"

    def __str__(self):
        return self.headline


class Testimonial(models.Model):
    """Customer testimonial model."""
    name = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Testimonial from {self.name}"


class BlogPost(models.Model):
    """Blog post model."""
    title = models.CharField(max_length=200)
    content = models.TextField()
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class Service(models.Model):
    """Service content displayed on the home and services pages."""
    title = models.CharField(max_length=160)
    description = models.TextField()
    home_image = models.ImageField(upload_to='services/home/')
    services_image = models.ImageField(upload_to='services/page/')
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'title']

    def __str__(self):
        return self.title


class MeetOurTeam(models.Model):
    image = models.ImageField(upload_to='team/')
    name = models.CharField(max_length=160)
    position = models.CharField(max_length=200)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Team member'
        verbose_name_plural = 'Team members'

    def __str__(self):
        return self.name


class Listing(models.Model):
    """Property listing displayed on the site."""
    landlord = models.ForeignKey(
        Landlord,
        on_delete=models.SET_NULL,
        related_name='properties',
        null=True,
        blank=True,
    )
    apartment_type = models.CharField(max_length=120)
    image = models.ImageField(upload_to='listings/')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    location = models.CharField(max_length=160)
    is_checked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.apartment_type} - {self.location}"


class ListingImage(models.Model):
    """Additional gallery image for a property listing."""
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='gallery_images',
    )
    image = models.ImageField(upload_to='listings/gallery/')
    caption = models.CharField(max_length=140, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.caption or f"Image for {self.listing.apartment_type}"


class ContactMessage(models.Model):
    """Contact form submissions from website visitors."""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact message'
        verbose_name_plural = 'Contact messages'

    def __str__(self):
        return f"Message from {self.name} - {self.subject}"
