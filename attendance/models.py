from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        ABSENT = 'ABSENT', 'Absent'
        HALF_DAY = 'HALF_DAY', 'Half day'
        ON_LEAVE = 'ON_LEAVE', 'On leave'
        HOLIDAY = 'HOLIDAY', 'Holiday'
        WEEK_OFF = 'WEEK_OFF', 'Week off'

    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='employee_attendance')
    date = models.DateField()
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PRESENT)
    working_hours = models.DurationField(default=timedelta(0))
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-pk']
        constraints = [
            models.UniqueConstraint(fields=['employee', 'date'], name='employee_attendance_unique_day'),
            models.UniqueConstraint(fields=['employee'], condition=models.Q(check_in__isnull=False, check_out__isnull=True), name='employee_one_open_attendance'),
            models.CheckConstraint(condition=models.Q(check_out__isnull=True) | (models.Q(check_in__isnull=False) & models.Q(check_out__gte=models.F('check_in'))), name='attendance_checkout_ordered'),
            models.CheckConstraint(condition=models.Q(working_hours__gte=timedelta(0)), name='attendance_hours_nonnegative'),
        ]

    def clean(self):
        if self.check_out and (not self.check_in or self.check_out < self.check_in):
            raise ValidationError({'check_out': 'Check out must be on or after check in.'})

    def save(self, *args, **kwargs):
        self.working_hours = self.check_out - self.check_in if self.check_in and self.check_out else timedelta(0)
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.employee} / {self.date}'


class AttendanceAuditLog(models.Model):
    attendance = models.ForeignKey(Attendance, on_delete=models.PROTECT, related_name='audit_logs')
    corrected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='attendance_corrections')
    reason = models.TextField()
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']


class LeaveRequest(models.Model):
    class Type(models.TextChoices):
        CASUAL = 'CASUAL', 'Casual'
        SICK = 'SICK', 'Sick'
        ANNUAL = 'ANNUAL', 'Annual'
        UNPAID = 'UNPAID', 'Unpaid'
        MATERNITY = 'MATERNITY', 'Maternity'
        PATERNITY = 'PATERNITY', 'Paternity'
        OTHER = 'OTHER', 'Other'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'

    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='leave_requests')
    leave_type = models.CharField(max_length=12, choices=Type.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    applied_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='reviewed_leaves')
    hr_comment = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-applied_at', '-pk']
        constraints = [models.CheckConstraint(condition=models.Q(end_date__gte=models.F('start_date')), name='leave_dates_ordered')]

    def clean(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': 'End date cannot be before start date.'})

    @property
    def calendar_days(self):
        return (self.end_date - self.start_date).days + 1

    @property
    def working_days(self):
        from .services import working_dates
        return len(working_dates(self.start_date, self.end_date))

    def __str__(self):
        return f'{self.employee}: {self.start_date} - {self.end_date}'


class LeaveAuditLog(models.Model):
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.PROTECT, related_name='history')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='leave_actions')
    action = models.CharField(max_length=10, choices=LeaveRequest.Status.choices)
    comment = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'pk']
