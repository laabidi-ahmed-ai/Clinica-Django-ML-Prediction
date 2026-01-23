from django.contrib import admin
from.models import *
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta

class PublicationAdmin(admin.ModelAdmin):
    list_display = ('title', 'date_pub', 'deadline', 'address')
    list_filter = ('date_pub', 'deadline')
    search_fields = ('title', 'description', 'address')
    ordering = ('-date_pub',)
    date_hierarchy = 'date_pub'
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('title', 'description')
        }),
        ('Dates et lieu', {
            'fields': ('date_pub', 'deadline', 'address')
        }),
        ('Média', {
            'fields': ('pubPicture',)
        }),
    )
    
    readonly_fields = ['date_pub']

    def duration(self, obj):
        """Calculer la durée en jours entre date_pub et delai"""
        if obj.date_pub and obj.deadline:
            return (obj.deadline - obj.date_pub).days
        return '-'
    duration.short_description = "Duration (by days)"
    
    def is_upcoming(self, obj):
        """Vérifier si la publication est à venir (dans les 7 prochains jours)"""
        today = timezone.now().date()
        if obj.deadline and obj.deadline <= today + timedelta(days=7):
            return format_html('<span style="color:red;font-weight:bold;">Soon!</span>')
        return '-'
    is_upcoming.short_description = "Upcoming?"


admin.site.register(Publication,PublicationAdmin)