import uuid
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


class TaskStatus(models.TextChoices):
    TODO = 'TODO', 'To do'
    IN_PROGRESS = 'IN_PROGRESS', 'In progress'
    BLOCKED = 'BLOCKED', 'Blocked'
    IN_REVIEW = 'IN_REVIEW', 'In review'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class Task(models.Model):
    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        URGENT = 'URGENT', 'Urgent'

    project = models.ForeignKey('projects.Project', on_delete=models.PROTECT, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='assigned_tasks')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_tasks')
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=15, choices=TaskStatus.choices, default=TaskStatus.TODO)
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    estimated_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))])
    actual_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))])
    progress_percentage = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(progress_percentage__gte=0, progress_percentage__lte=100), name='task_progress_range'),
            models.CheckConstraint(condition=models.Q(estimated_hours__gte=0, actual_hours__gte=0), name='task_hours_nonnegative'),
            models.CheckConstraint(condition=models.Q(start_date__isnull=True) | models.Q(due_date__isnull=True) | models.Q(due_date__gte=models.F('start_date')), name='task_dates_ordered'),
        ]

    def clean(self):
        if self.start_date and self.due_date and self.due_date < self.start_date:
            raise ValidationError({'due_date': 'Due date cannot be before start date.'})

    def save(self, *args, **kwargs):
        if self.status == TaskStatus.COMPLETED:
            self.progress_percentage = 100
            self.completed_at = self.completed_at or timezone.now()
        else:
            self.completed_at = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class TaskDailyUpdate(models.Model):
    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name='daily_updates')
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='task_daily_updates')
    work_date = models.DateField()
    work_description = models.TextField()
    hours_worked = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('24'))])
    progress_percentage = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    status = models.CharField(max_length=15, choices=TaskStatus.choices, default=TaskStatus.IN_PROGRESS)
    blockers = models.TextField(blank=True, default='')
    next_plan = models.TextField(blank=True, default='')
    employee_comment = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-work_date', '-created_at', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(progress_percentage__gte=0, progress_percentage__lte=100), name='daily_progress_range'),
            models.CheckConstraint(condition=models.Q(hours_worked__gte=0, hours_worked__lte=24), name='daily_hours_range'),
        ]

    def clean(self):
        if self.work_date and self.work_date > timezone.localdate():
            raise ValidationError({'work_date': 'Work date cannot be in the future.'})
        if self.task_id and self.work_date and self.task.start_date and self.work_date < self.task.start_date:
            raise ValidationError({'work_date': 'Work date cannot be before the task start date.'})

    def __str__(self):
        return f'{self.task} / {self.work_date}'


class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='task_comments')
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at', 'pk']


def task_attachment_path(instance, filename):
    return f'task_attachments/{instance.task_id}/{uuid.uuid4().hex}{Path(filename).suffix[:20]}'


class TaskAttachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name='attachments')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='task_attachments')
    file = models.FileField(upload_to=task_attachment_path)
    file_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']
