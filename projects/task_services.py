from decimal import Decimal
from django.db.models import Avg, Sum
from .models import Project, Task


def refresh_project_progress(project_id):
    # Lock the project so concurrent updates cannot overwrite a newer rollup.
    Project.objects.select_for_update().get(pk=project_id)
    progress = Task.objects.filter(project_id=project_id, is_active=True).exclude(status='CANCELLED').aggregate(value=Avg('progress_percentage'))['value']
    Project.objects.filter(pk=project_id).update(progress=round(progress or 0))


def apply_daily_update(task):
    task.actual_hours = task.daily_updates.aggregate(value=Sum('hours_worked'))['value'] or Decimal('0')
    latest = task.daily_updates.first()
    task.progress_percentage = latest.progress_percentage
    task.status = 'IN_REVIEW' if latest.status == 'COMPLETED' else latest.status
    task.save()
    refresh_project_progress(task.project_id)
