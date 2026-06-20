from django.contrib import admin
from .models import Client, Team, Project


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']
    ordering = ['name']


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']
    ordering = ['name']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'client', 'team', 'status', 'progress', 'delivery_date', 'created_at']
    list_filter = ['status', 'created_at', 'client', 'team']
    search_fields = ['name', 'description', 'client__name', 'team__name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'client', 'team')
        }),
        ('Project Details', {
            'fields': ('status', 'progress', 'delivery_date', 'github_url', 'people')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
