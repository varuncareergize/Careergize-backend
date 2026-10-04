from django.contrib import admin
from projects.task_permissions import is_hr_admin
from .models import Attendance, AttendanceAuditLog, LeaveRequest, LeaveAuditLog


class HRHistoryAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_view_permission(self, request, obj=None):
        return is_hr_admin(request.user)
    def has_module_permission(self, request):
        return is_hr_admin(request.user)


@admin.register(Attendance)
class AttendanceAdmin(HRHistoryAdmin):
    list_display = ['employee', 'date', 'check_in', 'check_out', 'status', 'working_hours']
    list_filter = ['date', 'status']
    search_fields = ['employee__username']


@admin.register(LeaveRequest)
class LeaveRequestAdmin(HRHistoryAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'status', 'reviewed_by']
    list_filter = ['status', 'leave_type']


admin.site.register(AttendanceAuditLog, HRHistoryAdmin)
admin.site.register(LeaveAuditLog, HRHistoryAdmin)
