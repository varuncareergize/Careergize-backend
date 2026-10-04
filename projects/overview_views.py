from collections import Counter
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.response import Response
from attendance.views import EmployeeView, query_values
from attendance.models import Attendance, LeaveRequest
from attendance.services import today, company_timezone
from django.utils import timezone
from .models import Project, TaskDailyUpdate
from .task_permissions import is_hr_admin, is_manager, visible_tasks


class OverviewView(EmployeeView):
    def get(self, request):
        day = query_values(request).get('date', today())
        user = request.user
        hr, manager = is_hr_admin(user), is_manager(user)
        projects = Project.objects.filter(is_active=True)
        if not hr:
            access = Q(assigned_users=user) | Q(tasks__assigned_to=user)
            if manager:
                access |= Q(project_manager=user)
            projects = projects.filter(access).distinct()
        tasks = list(visible_tasks(user).filter(is_active=True, project__is_active=True))
        employees = get_user_model().objects.filter(is_active=True)
        if not hr:
            if manager:
                ids = set(Project.objects.filter(project_manager=user, is_active=True).values_list('assigned_users', flat=True))
                ids.update(t.assigned_to_id for t in tasks if t.project.project_manager_id == user.pk)
                ids.add(user.pk)
                employees = employees.filter(pk__in=ids)
            else:
                employees = employees.filter(pk=user.pk)
        employees = list(employees.select_related('profile__department').order_by('first_name', 'username'))
        ids = [e.pk for e in employees]
        attendance = {r.employee_id: r for r in Attendance.objects.filter(date=day, employee_id__in=ids)}
        leave = set(LeaveRequest.objects.filter(employee_id__in=ids, status='APPROVED', start_date__lte=day, end_date__gte=day).values_list('employee_id', flat=True))
        members = []
        for employee in employees:
            record = attendance.get(employee.pk)
            profile = getattr(employee, 'profile', None)
            members.append({'id': employee.pk, 'name': employee.get_full_name() or employee.username,
                'department': profile.department.name if profile and profile.department else 'Employee',
                'status': record.status if record else 'ON_LEAVE' if employee.pk in leave else 'ABSENT',
                'marked': record is not None})
        counts = Counter(m['status'] for m in members)
        task_counts = Counter(t.status for t in tasks)
        activity = []
        start = day - timedelta(days=6)
        updates = Counter(TaskDailyUpdate.objects.filter(task_id__in=[t.pk for t in tasks], work_date__range=[start, day]).values_list('work_date', flat=True))
        for offset in range(7):
            date = start + timedelta(days=offset)
            activity.append({'date': date, 'updates': updates[date],
                'created': sum(timezone.localtime(t.created_at, company_timezone()).date() == date for t in tasks),
                'completed': sum(bool(t.completed_at) and timezone.localtime(t.completed_at, company_timezone()).date() == date for t in tasks)})
        return Response({'date': day, 'name': user.get_full_name() or user.username,
            'scope': 'Company' if hr else 'Managed team' if manager else 'My attendance',
            'summary': {'projects': projects.exclude(status__in=['Completed', 'Delivered']).count(),
                'completed': task_counts['COMPLETED'], 'pending': sum(t.status not in ['COMPLETED', 'CANCELLED'] for t in tasks),
                'members': len(members), 'present': counts['PRESENT'], 'absent': counts['ABSENT'], 'leave': counts['ON_LEAVE'], 'half_day': counts['HALF_DAY']},
            'projects': list(projects.values('id', 'name', 'status', 'progress', 'expected_delivery_date')),
            'tasks': [{'id': t.pk, 'title': t.title, 'project': t.project.name, 'status': t.status,
                'priority': t.priority, 'due_date': t.due_date, 'assigned_to': t.assigned_to.get_full_name() or t.assigned_to.username} for t in tasks],
            'members': members, 'activity': activity, 'task_counts': task_counts})
