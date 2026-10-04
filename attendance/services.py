from datetime import date, timedelta
from zoneinfo import ZoneInfo
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from .models import Attendance, AttendanceAuditLog, LeaveRequest, LeaveAuditLog


def company_timezone():
    return ZoneInfo(getattr(settings, 'EMPLOYEE_TIME_ZONE', settings.TIME_ZONE))


def today():
    return timezone.localtime(timezone.now(), company_timezone()).date()


def holidays():
    return {date.fromisoformat(value) for value in getattr(settings, 'EMPLOYEE_HOLIDAYS', [])}


def day_status(day):
    if day in holidays():
        return 'HOLIDAY'
    if day.weekday() in getattr(settings, 'EMPLOYEE_WEEK_OFF_DAYS', [5, 6]):
        return 'WEEK_OFF'
    return None


def working_dates(start, end):
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1) if not day_status(start + timedelta(days=offset))]


def lock_employee(employee):
    get_user_model().objects.select_for_update().get(pk=employee.pk)


def snapshot(record):
    return {key: str(getattr(record, key)) if getattr(record, key) is not None else None for key in ['date', 'check_in', 'check_out', 'status', 'working_hours', 'notes']}


@transaction.atomic
def check_in(employee):
    lock_employee(employee)
    day = today()
    if Attendance.objects.filter(employee=employee, check_in__isnull=False, check_out__isnull=True).exists():
        raise ValidationError('You already have an open attendance record. Check out first.')
    if LeaveRequest.objects.filter(employee=employee, status='APPROVED', start_date__lte=day, end_date__gte=day).exists() and not day_status(day):
        raise ValidationError('You are on approved leave today.')
    record = Attendance.objects.select_for_update().filter(employee=employee, date=day).first()
    if record and (record.check_in or record.status in ['ON_LEAVE', 'HOLIDAY', 'WEEK_OFF']):
        raise ValidationError('Attendance is already recorded or this day is marked as leave/off.')
    # Working on a weekend/holiday is allowed; the actual attendance takes precedence.
    record = record or Attendance(employee=employee, date=day)
    record.check_in = timezone.now()
    record.status = 'PRESENT'
    record.save()
    return record


@transaction.atomic
def check_out(employee):
    lock_employee(employee)
    record = Attendance.objects.select_for_update().filter(employee=employee, check_in__isnull=False, check_out__isnull=True).order_by('-date', '-pk').first()
    if not record:
        raise ValidationError('You must check in before checking out, and can check out only once.')
    record.check_out = timezone.now()
    if record.check_out < record.check_in:
        raise ValidationError('Check out cannot be earlier than check in.')
    record.save()
    return record


@transaction.atomic
def apply_leave(employee, values):
    lock_employee(employee)
    start, end = values['start_date'], values['end_date']
    if end < start:
        raise ValidationError({'end_date': 'End date cannot be before start date.'})
    if (end - start).days > 365:
        raise ValidationError({'end_date': 'A leave request cannot exceed 366 calendar days.'})
    if start < today() and not getattr(settings, 'ALLOW_BACKDATED_LEAVE', False):
        raise ValidationError({'start_date': 'Backdated leave is not allowed.'})
    if LeaveRequest.objects.filter(employee=employee, status__in=['PENDING', 'APPROVED'], start_date__lte=end, end_date__gte=start).exists():
        raise ValidationError('You already have a pending or approved leave overlapping these dates.')
    leave = LeaveRequest.objects.create(employee=employee, **values)
    LeaveAuditLog.objects.create(leave_request=leave, actor=employee, action='PENDING', comment=leave.reason)
    return leave


@transaction.atomic
def review_leave(leave_id, reviewer, decision, comment):
    # Use the same employee lock as check-in and leave application.
    employee_id = LeaveRequest.objects.get(pk=leave_id).employee_id
    employee = get_user_model().objects.get(pk=employee_id)
    lock_employee(employee)
    leave = LeaveRequest.objects.select_for_update().get(pk=leave_id)
    if leave.employee_id == reviewer.pk:
        raise ValidationError('You cannot review your own leave request.')
    if leave.status != 'PENDING':
        raise ValidationError('Only pending leave requests can be reviewed.')
    if decision == 'APPROVED':
        dates = working_dates(leave.start_date, leave.end_date)
        if Attendance.objects.filter(employee=employee, date__in=dates, check_in__isnull=False).exists():
            raise ValidationError('Attendance is already recorded during this leave. Correct the attendance before approving.')
        for day in dates:
            record, created = Attendance.objects.get_or_create(employee=employee, date=day, defaults={'status': 'ON_LEAVE'})
            if not created and record.status != 'ON_LEAVE':
                before = snapshot(record)
                record.status = 'ON_LEAVE'
                record.save()
                AttendanceAuditLog.objects.create(attendance=record, corrected_by=reviewer, reason=f'Leave request #{leave.pk} approved', before=before, after=snapshot(record))
    leave.status = decision
    leave.reviewed_by = reviewer
    leave.reviewed_at = timezone.now()
    leave.hr_comment = comment
    leave.save()
    LeaveAuditLog.objects.create(leave_request=leave, actor=reviewer, action=decision, comment=comment)
    return leave


@transaction.atomic
def cancel_leave(leave_id, employee):
    lock_employee(employee)
    leave = LeaveRequest.objects.select_for_update().get(pk=leave_id, employee=employee)
    if leave.status != 'PENDING':
        raise ValidationError('Only pending leave requests can be cancelled.')
    leave.status = 'CANCELLED'
    leave.save()
    LeaveAuditLog.objects.create(leave_request=leave, actor=employee, action='CANCELLED')
    return leave
