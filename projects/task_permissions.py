from django.db.models import Q
from .models import Project, Task, UserProfile


def department_name(user):
    if not user.is_authenticated:
        return None
    return UserProfile.objects.filter(user=user).values_list('department__name', flat=True).first()


def is_hr_admin(user):
    if not user.is_authenticated:
        return False
    department = department_name(user)
    if department:
        return department == 'HR'
    # Django staff access alone does not grant business-management permissions.
    return user.is_superuser or user.groups.filter(name__in=['HR', 'Admin']).exists()


def is_manager(user):
    if not user.is_authenticated:
        return False
    department = department_name(user)
    if department:
        return department == 'Manager'
    return user.groups.filter(name__in=['Manager', 'Project Manager']).exists() or Project.objects.filter(project_manager=user).exists()


def can_manage_project(user, project):
    return is_hr_admin(user) or (is_manager(user) and project.project_manager_id == user.pk)


def visible_tasks(user):
    tasks = Task.objects.select_related('project', 'assigned_to', 'created_by')
    if is_hr_admin(user):
        return tasks
    access = Q(assigned_to=user)
    if is_manager(user):
        access |= Q(project__project_manager=user)
    return tasks.filter(access).distinct()


def manageable_projects(user):
    if is_hr_admin(user):
        return Project.objects.all()
    if is_manager(user):
        return Project.objects.filter(project_manager=user)
    return Project.objects.none()


def role_capabilities(user):
    hr = is_hr_admin(user)
    manager = is_manager(user)
    profile = UserProfile.objects.select_related('department').filter(user=user).first()
    return {
        'role': 'HR/Admin' if hr else 'Manager' if manager else 'Employee',
        'department': profile.department.name if profile and profile.department else None,
        'can_create_project': hr or manager,
        'can_create_task': hr or manager,
        'can_delete': hr or manager,
        'is_hr_admin': hr,
    }
