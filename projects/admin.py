from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from .models import Client, Team, Project, Department, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    extra = 1
    max_num = 1
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Contact', {'fields': ('phone_number', 'address', 'city', 'state', 'postal_code', 'country')}),
        ('Personal details', {'fields': ('department', 'date_of_birth')}),
        ('Bank details', {'fields': ('bank_name', 'bank_account_holder_name', 'bank_account_number', 'bank_ifsc_code', 'bank_branch'), 'classes': ('collapse',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    verbose_name = 'User profile'
    verbose_name_plural = 'User profile'


class ProfileUserAdmin(UserAdmin):
    inlines = [UserProfileInline]


admin.site.unregister(get_user_model())
admin.site.register(get_user_model(), ProfileUserAdmin)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    readonly_fields = ['created_at']


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'email', 'phone', 'client_type', 'status', 'assigned_to']
    list_filter = ['client_type', 'status', 'industry', 'source']
    search_fields = ['name', 'contact_person', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']
    ordering = ['name']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'client', 'team', 'status', 'progress', 'expected_delivery_date', 'created_at']
    list_filter = ['priority', 'project_type', 'status', 'created_at', 'client', 'team']
    search_fields = ['name', 'description', 'client__name', 'team__name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'client', 'project_type', 'team', 'project_manager')
        }),
        ('Project Details', {
            'fields': ('status', 'priority', 'progress', 'start_date', 'expected_delivery_date', 'actual_delivery_date', 'website_url', 'github_url', 'assigned_users')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


from django.db import transaction
from .models import Task, TaskDailyUpdate, TaskComment, TaskAttachment
from .task_services import refresh_project_progress


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'assigned_to', 'priority', 'status', 'progress_percentage', 'due_date', 'is_active']
    list_filter = ['status', 'priority', 'is_active', 'project']
    search_fields = ['title', 'description', 'assigned_to__username']
    readonly_fields = ['created_by', 'actual_hours', 'created_at', 'updated_at', 'completed_at']

    def has_delete_permission(self, request, obj=None):
        return False

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        previous_project = Task.objects.get(pk=obj.pk).project_id if change else None
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        refresh_project_progress(obj.project_id)
        if previous_project and previous_project != obj.project_id:
            refresh_project_progress(previous_project)


class TaskHistoryAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(TaskDailyUpdate)
class TaskDailyUpdateAdmin(TaskHistoryAdmin):
    list_display = ['task', 'employee', 'work_date', 'hours_worked', 'progress_percentage', 'status']
    list_filter = ['work_date', 'status', 'employee']


@admin.register(TaskComment)
class TaskCommentAdmin(TaskHistoryAdmin):
    list_display = ['task', 'user', 'created_at']


@admin.register(TaskAttachment)
class TaskAttachmentAdmin(TaskHistoryAdmin):
    # Files are downloaded through the permission-checked API, not public media URLs.
    exclude = ['file']
    list_display = ['task', 'uploaded_by', 'file_name', 'created_at']

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields if field.name != 'file']
