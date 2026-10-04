import calendar
from collections import Counter
from datetime import date
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.exceptions import ValidationError as ModelValidationError
from django.shortcuts import get_object_or_404
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers
from projects.models import Department
from projects.task_permissions import is_hr_admin
from .models import Attendance, AttendanceAuditLog, LeaveRequest
from .serializers import AttendanceSerializer, AttendanceCorrectionSerializer, AttendanceAuditSerializer, LeaveSerializer, LeaveReviewSerializer
from .services import today, day_status, working_dates, check_in, check_out, apply_leave, review_leave, cancel_leave, lock_employee, snapshot


class QuerySerializer(serializers.Serializer):
    employee = serializers.IntegerField(min_value=1, required=False)
    department = serializers.IntegerField(min_value=1, required=False)
    date = serializers.DateField(required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    month = serializers.RegexField(r'^\d{4}-\d{2}$', required=False)


def query_values(request):
    serializer = QuerySerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def period(values):
    current = today()
    if 'month' in values:
        try:
            year, month = map(int, values['month'].split('-'))
            first = date(year, month, 1)
        except ValueError:
            raise ValidationError({'month': 'Enter a valid YYYY-MM month.'})
    else:
        first = current.replace(day=1)
    start = values.get('start_date', first)
    end = values.get('end_date', first.replace(day=calendar.monthrange(first.year, first.month)[1]))
    if end < start or (end - start).days > 365:
        raise ValidationError('Choose an ordered date range of up to 366 days.')
    return start, end


class EmployeeView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def require_hr(self, request):
        if not is_hr_admin(request.user):
            raise PermissionDenied('This action is restricted to HR/Admin.')


class AttendanceOptionsView(EmployeeView):
    def get(self, request):
        from django.conf import settings
        hr = is_hr_admin(request.user)
        users = get_user_model().objects.filter(is_active=True).select_related('profile__department') if hr else get_user_model().objects.filter(pk=request.user.pk).select_related('profile__department')
        employees = []
        for user in users:
            profile = getattr(user, 'profile', None)
            employees.append({'id': user.pk, 'name': user.get_full_name() or user.username, 'department_id': profile.department_id if profile else None})
        return Response({'today': today(), 'timezone': settings.EMPLOYEE_TIME_ZONE, 'is_hr_admin': hr, 'user_id': request.user.pk,
            'employees': employees, 'departments': list(Department.objects.values('id', 'name')) if hr else [],
            'week_off_days': settings.EMPLOYEE_WEEK_OFF_DAYS, 'holidays': settings.EMPLOYEE_HOLIDAYS,
            'allow_backdated_leave': settings.ALLOW_BACKDATED_LEAVE})


class AttendanceTodayView(EmployeeView):
    def get(self, request):
        record = Attendance.objects.filter(employee=request.user, date=today()).first()
        active = Attendance.objects.filter(employee=request.user, check_in__isnull=False, check_out__isnull=True).first()
        return Response({'date': today(), 'attendance': AttendanceSerializer(record).data if record else None,
            'active_attendance': AttendanceSerializer(active).data if active else None,
            'day_status': record.status if record else day_status(today()) or 'NOT_MARKED'})


class CheckInView(EmployeeView):
    def post(self, request):
        return Response(AttendanceSerializer(check_in(request.user)).data, status=201)


class CheckOutView(EmployeeView):
    def post(self, request):
        return Response(AttendanceSerializer(check_out(request.user)).data)


class AttendanceHistoryView(EmployeeView):
    def get(self, request):
        values = query_values(request)
        start, end = period(values)
        rows = Attendance.objects.select_related('employee__profile__department').filter(date__range=[start, end])
        hr_all = request.query_params.get('view') == 'all'
        if hr_all:
            self.require_hr(request)
            if values.get('employee'):
                rows = rows.filter(employee_id=values['employee'])
            if values.get('department'):
                rows = rows.filter(employee__profile__department_id=values['department'])
        else:
            rows = rows.filter(employee=request.user)
        counts = Counter(rows.values_list('status', flat=True))
        summary = {'working_days': len(working_dates(start, end)), 'present': counts['PRESENT'], 'absent': counts['ABSENT'], 'half_day': counts['HALF_DAY'], 'leave': counts['ON_LEAVE'], 'holiday': counts['HOLIDAY'], 'week_off': counts['WEEK_OFF']}
        status = request.query_params.get('status')
        if status:
            if status not in Attendance.Status.values:
                raise ValidationError({'status': 'Choose a valid attendance status.'})
            rows = rows.filter(status=status)
        return Response({'records': AttendanceSerializer(rows, many=True).data, 'summary': summary, 'start_date': start, 'end_date': end})


class HRAttendanceView(EmployeeView):
    def get(self, request):
        self.require_hr(request)
        values = query_values(request)
        day = values.get('date', today())
        users = get_user_model().objects.filter(is_active=True).select_related('profile__department')
        if values.get('employee'):
            users = users.filter(pk=values['employee'])
        if values.get('department'):
            users = users.filter(profile__department_id=values['department'])
        ids = list(users.values_list('pk', flat=True))
        records = {r.employee_id: r for r in Attendance.objects.filter(date=day, employee_id__in=ids).select_related('employee__profile__department')}
        leave_ids = set(LeaveRequest.objects.filter(employee_id__in=ids, status='APPROVED', start_date__lte=day, end_date__gte=day).values_list('employee_id', flat=True))
        rows = []
        for user in users:
            if user.pk in records:
                row = dict(AttendanceSerializer(records[user.pk]).data)
            else:
                profile = getattr(user, 'profile', None)
                row = {'id': None, 'employee': user.pk, 'employee_name': user.username, 'department': profile.department.name if profile and profile.department else None,
                    'date': day.isoformat(), 'status': 'ON_LEAVE' if user.pk in leave_ids else 'ABSENT', 'check_in': None, 'check_out': None, 'working_seconds': 0, 'notes': ''}
            rows.append(row)
        counts = Counter(row['status'] for row in rows)
        summary = {'total_employees': len(rows), 'present': counts['PRESENT'], 'absent': counts['ABSENT'], 'half_day': counts['HALF_DAY'], 'leave': counts['ON_LEAVE'], 'not_checked_in': counts['NOT_MARKED'], 'holiday': counts['HOLIDAY'], 'week_off': counts['WEEK_OFF']}
        if request.query_params.get('status'):
            rows = [row for row in rows if row['status'] == request.query_params['status']]
        return Response({'date': day, 'records': rows, 'summary': summary})


class AttendanceCorrectionView(EmployeeView):
    @transaction.atomic
    def post(self, request):
        self.require_hr(request)
        serializer = AttendanceCorrectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        employee, day, reason = values.pop('employee'), values.pop('date'), values.pop('correction_reason')
        lock_employee(employee)
        record = Attendance.objects.select_for_update().filter(employee=employee, date=day).first()
        before = snapshot(record) if record else {}
        record = record or Attendance(employee=employee, date=day)
        for key, value in values.items():
            setattr(record, key, value)
        if record.check_out and (not record.check_in or record.check_out < record.check_in):
            raise ValidationError({'check_out': 'Check out must be on or after check in.'})
        if record.check_in and record.status not in ['PRESENT', 'HALF_DAY']:
            raise ValidationError({'status': 'A checked-in record must be Present or Half Day. Clear the timestamps to change this.'})
        if record.check_in and not record.check_out and Attendance.objects.filter(employee=employee, check_in__isnull=False, check_out__isnull=True).exclude(pk=record.pk).exists():
            raise ValidationError({'check_out': 'This employee already has another open attendance record.'})
        record.save()
        AttendanceAuditLog.objects.create(attendance=record, corrected_by=request.user, reason=reason, before=before, after=snapshot(record))
        return Response(AttendanceSerializer(record).data)


class AttendanceAuditView(EmployeeView):
    def get(self, request, pk):
        rows = Attendance.objects.all() if is_hr_admin(request.user) else Attendance.objects.filter(employee=request.user)
        record = get_object_or_404(rows, pk=pk)
        return Response(AttendanceAuditSerializer(record.audit_logs.select_related('corrected_by'), many=True).data)


class LeaveListView(EmployeeView):
    def get(self, request):
        values = query_values(request)
        rows = LeaveRequest.objects.select_related('employee__profile__department', 'reviewed_by').prefetch_related('history__actor')
        if request.query_params.get('view') == 'all':
            self.require_hr(request)
            if values.get('employee'):
                rows = rows.filter(employee_id=values['employee'])
            if values.get('department'):
                rows = rows.filter(employee__profile__department_id=values['department'])
        else:
            rows = rows.filter(employee=request.user)
        if request.query_params.get('status'):
            if request.query_params['status'] not in LeaveRequest.Status.values:
                raise ValidationError({'status': 'Choose a valid leave status.'})
            rows = rows.filter(status=request.query_params['status'])
        if values.get('start_date'):
            rows = rows.filter(end_date__gte=values['start_date'])
        if values.get('end_date'):
            rows = rows.filter(start_date__lte=values['end_date'])
        return Response(LeaveSerializer(rows, many=True).data)

    def post(self, request):
        serializer = LeaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = {key: value for key, value in serializer.validated_data.items() if key in ['leave_type', 'start_date', 'end_date', 'reason']}
        leave = apply_leave(request.user, values)
        return Response(LeaveSerializer(leave).data, status=201)


class LeaveReviewView(EmployeeView):
    def post(self, request, pk):
        self.require_hr(request)
        get_object_or_404(LeaveRequest, pk=pk)
        serializer = LeaveReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(LeaveSerializer(review_leave(pk, request.user, serializer.validated_data['status'], serializer.validated_data['hr_comment'])).data)


class LeaveCancelView(EmployeeView):
    def post(self, request, pk):
        get_object_or_404(LeaveRequest, pk=pk, employee=request.user)
        return Response(LeaveSerializer(cancel_leave(pk, request.user)).data)
