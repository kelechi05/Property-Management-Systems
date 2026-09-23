from django.contrib import admin
from .models import BlogPost, HeroSection, Listing, ListingImage, MeetOurTeam, Service, Testimonial, ContactMessage


@admin.register(HeroSection)
class HeroSectionAdmin(admin.ModelAdmin):
    list_display = ("headline", "sort_order", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("headline", "blurb")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("sort_order", "-created_at")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name", "content")
    readonly_fields = ("created_at",)


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "published", "created_at")
    list_filter = ("published", "created_at")
    search_fields = ("title", "content")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "sort_order", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("title", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(MeetOurTeam)
class MeetOurTeamAdmin(admin.ModelAdmin):
    list_display = ("name", "position", "sort_order", "created_at")
    search_fields = ("name", "position")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("sort_order", "name")


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1
    fields = ("image", "caption", "sort_order")


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("apartment_type", "landlord", "price", "location", "is_checked", "created_at")
    list_filter = ("is_checked", "created_at", "landlord")
    search_fields = ("apartment_type", "description", "location", "landlord__user__username", "landlord__email")
    readonly_fields = ("created_at", "updated_at")
    inlines = (ListingImageInline,)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ('Message Information', {
            'fields': ('name', 'email', 'subject', 'message')
        }),
        ('Status', {
            'fields': ('is_read',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
