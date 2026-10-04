from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from projects.models import Department
from .models import Attendance, AttendanceAuditLog, LeaveRequest
from .services import today, company_timezone


class AttendanceLeaveTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.employee = User.objects.create_user(username='it-employee', is_staff=True)
        self.employee.profile.department = Department.objects.create(name='IT')
        self.employee.profile.save()
        self.other = User.objects.create_user(username='other-employee')
        self.hr = User.objects.create_user(username='hr')
        self.hr.profile.department = Department.objects.create(name='HR')
        self.hr.profile.save()
        self.manager = User.objects.create_user(username='manager')
        self.manager.profile.department = Department.objects.create(name='Manager')
        self.manager.profile.save()
        self.api = APIClient()
        self.api.force_authenticate(user=self.employee)

    def leave(self, **values):
        payload = {'leave_type': 'CASUAL', 'start_date': str(today() + timedelta(days=2)), 'end_date': str(today() + timedelta(days=4)), 'reason': 'Personal work'}
        payload.update(values)
        return self.api.post('/api/leaves/', payload, format='json')

    def test_anonymous_attendance_and_leave_access_denied(self):
        self.api.force_authenticate(user=None)
        for path in ['/api/attendance/today/', '/api/attendance/history/', '/api/leaves/', '/api/attendance/hr/']:
            self.assertEqual(self.api.get(path).status_code, 403)

    def test_server_check_in_and_check_out_calculate_exact_hours(self):
        start = timezone.now()
        with patch('attendance.services.timezone.now', return_value=start):
            response = self.api.post('/api/attendance/check-in/', {'employee': self.other.pk, 'check_in': '2000-01-01T00:00:00Z', 'working_hours': 99}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        record = Attendance.objects.get(pk=response.data['id'])
        self.assertEqual(record.employee_id, self.employee.pk)
        self.assertEqual(record.check_in, start)
        self.assertTrue(timezone.is_aware(record.check_in))
        self.assertEqual(record.status, 'PRESENT')
        with patch('attendance.services.timezone.now', return_value=start + timedelta(hours=8, minutes=43)):
            response = self.api.post('/api/attendance/check-out/', {}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['working_seconds'], 8 * 3600 + 43 * 60)
        record.refresh_from_db()
        self.assertEqual(record.working_hours, timedelta(hours=8, minutes=43))

    def test_check_in_and_check_out_cannot_be_repeated(self):
        self.assertEqual(self.api.post('/api/attendance/check-out/').status_code, 400)
        self.assertEqual(self.api.post('/api/attendance/check-in/').status_code, 201)
        self.assertEqual(self.api.post('/api/attendance/check-in/').status_code, 400)
        self.assertEqual(self.api.post('/api/attendance/check-out/').status_code, 200)
        self.assertEqual(self.api.post('/api/attendance/check-out/').status_code, 400)
        self.assertEqual(self.api.post('/api/attendance/check-in/').status_code, 400)
        self.assertEqual(Attendance.objects.filter(employee=self.employee, date=today()).count(), 1)

    def test_overnight_attendance_can_be_checked_out(self):
        start = timezone.now() - timedelta(days=1)
        record = Attendance.objects.create(employee=self.employee, date=timezone.localtime(start, company_timezone()).date(), check_in=start)
        response = self.api.get('/api/attendance/today/')
        self.assertEqual(response.data['active_attendance']['id'], record.pk)
        self.assertEqual(self.api.post('/api/attendance/check-in/').status_code, 400)
        self.assertEqual(self.api.post('/api/attendance/check-out/').status_code, 200)

    def test_database_prevents_duplicate_daily_records(self):
        Attendance.objects.create(employee=self.employee, date=today())
        with self.assertRaises(IntegrityError), transaction.atomic():
            Attendance.objects.create(employee=self.employee, date=today())

    def test_personal_history_is_scoped_and_filterable(self):
        Attendance.objects.create(employee=self.employee, date=today(), status='PRESENT')
        Attendance.objects.create(employee=self.other, date=today(), status='ABSENT')
        response = self.api.get('/api/attendance/history/', {'month': str(today())[:7], 'status': 'PRESENT', 'employee': self.other.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['records']), 1)
        self.assertEqual(response.data['records'][0]['employee'], self.employee.pk)
        self.assertEqual(response.data['summary']['present'], 1)
        self.assertEqual(self.api.get('/api/attendance/history/?view=all').status_code, 403)
        self.assertEqual(self.api.get('/api/attendance/history/?month=2026-99').status_code, 400)
        self.assertEqual(self.api.get('/api/attendance/history/?start_date=2026-12-01&end_date=2026-01-01').status_code, 400)

    def test_hr_roster_filters_department_and_includes_unmarked_employees(self):
        self.api.force_authenticate(user=self.hr)
        with override_settings(EMPLOYEE_WEEK_OFF_DAYS=[], EMPLOYEE_HOLIDAYS=[]):
            response = self.api.get('/api/attendance/hr/', {'date': str(today()), 'department': self.employee.profile.department_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['records']), 1)
        self.assertEqual(response.data['records'][0]['status'], 'ABSENT')
        self.assertEqual(response.data['summary']['absent'], 1)
        self.api.force_authenticate(user=self.manager)
        self.assertEqual(self.api.get('/api/attendance/hr/').status_code, 403)

    def test_only_hr_can_correct_and_every_correction_is_audited(self):
        start = timezone.now() - timedelta(hours=10)
        day = timezone.localtime(start, company_timezone()).date()
        record = Attendance.objects.create(employee=self.employee, date=day, check_in=start, check_out=start + timedelta(hours=7))
        payload = {'employee': self.employee.pk, 'date': str(day), 'status': 'PRESENT', 'check_out': (start + timedelta(hours=8)).isoformat(), 'working_hours': 500, 'notes': 'Corrected checkout', 'correction_reason': 'Employee forgot to record the final hour'}
        self.assertEqual(self.api.post('/api/attendance/hr/correct/', payload, format='json').status_code, 403)
        self.api.force_authenticate(user=self.hr)
        response = self.api.post('/api/attendance/hr/correct/', payload, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['working_seconds'], 8 * 3600)
        log = AttendanceAuditLog.objects.get(attendance=record)
        self.assertEqual(log.corrected_by_id, self.hr.pk)
        self.assertNotEqual(log.before['check_out'], log.after['check_out'])
        self.api.force_authenticate(user=self.employee)
        self.assertEqual(len(self.api.get(f'/api/attendance/{record.pk}/audit/').data), 1)
        self.api.force_authenticate(user=self.other)
        self.assertEqual(self.api.get(f'/api/attendance/{record.pk}/audit/').status_code, 404)

    def test_hr_correction_rejects_invalid_times_and_records_absence(self):
        self.api.force_authenticate(user=self.hr)
        payload = {'employee': self.employee.pk, 'date': str(today()), 'status': 'ABSENT', 'notes': 'No attendance', 'correction_reason': 'Verified with supervisor'}
        self.assertEqual(self.api.post('/api/attendance/hr/correct/', payload, format='json').status_code, 200)
        payload.update(status='PRESENT', check_out=timezone.now().isoformat())
        self.assertEqual(self.api.post('/api/attendance/hr/correct/', payload, format='json').status_code, 400)
        payload.update(check_in=(timezone.now() + timedelta(hours=1)).isoformat())
        self.assertEqual(self.api.post('/api/attendance/hr/correct/', payload, format='json').status_code, 400)

    def test_leave_application_calculates_days_and_records_history(self):
        response = self.leave(employee=self.other.pk, status='APPROVED', reviewed_by=self.employee.pk)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['employee'], self.employee.pk)
        self.assertEqual(response.data['status'], 'PENDING')
        self.assertEqual(response.data['calendar_days'], 3)
        self.assertIsNone(response.data['reviewed_by'])
        self.assertEqual(response.data['history'][0]['action'], 'PENDING')

    def test_leave_date_and_overlap_validation(self):
        self.assertEqual(self.leave(start_date=str(today() - timedelta(days=1))).status_code, 400)
        self.assertEqual(self.leave(start_date=str(today() + timedelta(days=5)), end_date=str(today() + timedelta(days=2))).status_code, 400)
        self.assertEqual(self.leave().status_code, 201)
        self.assertEqual(self.leave().status_code, 400)
        self.assertEqual(self.leave(start_date=str(today() + timedelta(days=4)), end_date=str(today() + timedelta(days=6))).status_code, 400)

    def test_hr_approval_marks_working_leave_days_and_blocks_check_in(self):
        with override_settings(EMPLOYEE_WEEK_OFF_DAYS=[], EMPLOYEE_HOLIDAYS=[]):
            response = self.leave(start_date=str(today()), end_date=str(today() + timedelta(days=2)))
            leave_id = response.data['id']
            self.api.force_authenticate(user=self.hr)
            response = self.api.post(f'/api/leaves/{leave_id}/review/', {'status': 'APPROVED', 'hr_comment': 'Approved by HR'}, format='json')
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data['reviewed_by'], self.hr.pk)
            self.assertEqual(response.data['history'][-1]['action'], 'APPROVED')
            self.assertEqual(Attendance.objects.filter(employee=self.employee, status='ON_LEAVE').count(), 3)
            self.api.force_authenticate(user=self.employee)
            self.assertEqual(self.api.post('/api/attendance/check-in/').status_code, 400)
            self.assertEqual(self.api.post(f'/api/leaves/{leave_id}/cancel/').status_code, 400)
            self.assertEqual(self.api.patch('/api/leaves/', {'reason': 'Change approved leave'}, format='json').status_code, 405)

    def test_manager_and_employee_cannot_review_leave(self):
        leave_id = self.leave().data['id']
        for actor in [self.employee, self.manager]:
            self.api.force_authenticate(user=actor)
            self.assertEqual(self.api.post(f'/api/leaves/{leave_id}/review/', {'status': 'APPROVED'}, format='json').status_code, 403)

    def test_hr_cannot_review_own_leave(self):
        self.api.force_authenticate(user=self.hr)
        leave_id = self.leave().data['id']
        self.assertEqual(self.api.post(f'/api/leaves/{leave_id}/review/', {'status': 'APPROVED'}, format='json').status_code, 400)

    def test_pending_leave_can_be_cancelled_and_dates_reused(self):
        leave_id = self.leave().data['id']
        self.api.force_authenticate(user=self.other)
        self.assertEqual(self.api.post(f'/api/leaves/{leave_id}/cancel/').status_code, 404)
        self.api.force_authenticate(user=self.employee)
        response = self.api.post(f'/api/leaves/{leave_id}/cancel/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['history'][-1]['action'], 'CANCELLED')
        self.assertEqual(self.leave().status_code, 201)

    def test_rejection_does_not_create_leave_attendance(self):
        leave_id = self.leave().data['id']
        self.api.force_authenticate(user=self.hr)
        response = self.api.post(f'/api/leaves/{leave_id}/review/', {'status': 'REJECTED', 'hr_comment': 'Please choose another date'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Attendance.objects.filter(employee=self.employee).count(), 0)
        self.assertEqual(self.api.post(f'/api/leaves/{leave_id}/review/', {'status': 'APPROVED'}, format='json').status_code, 400)
        self.api.force_authenticate(user=self.employee)
        self.assertEqual(self.api.get('/api/leaves/').data[0]['hr_comment'], 'Please choose another date')

    def test_leave_cannot_overwrite_actual_work(self):
        with override_settings(EMPLOYEE_WEEK_OFF_DAYS=[]):
            leave_id = self.leave(start_date=str(today()), end_date=str(today())).data['id']
            self.assertEqual(self.api.post('/api/attendance/check-in/').status_code, 201)
            self.api.force_authenticate(user=self.hr)
            self.assertEqual(self.api.post(f'/api/leaves/{leave_id}/review/', {'status': 'APPROVED'}, format='json').status_code, 400)
            self.assertEqual(LeaveRequest.objects.get(pk=leave_id).status, 'PENDING')

    def test_holiday_and_weekend_counts_and_backdated_setting(self):
        # 5 October 2026 is Monday; 10/11 October are Saturday/Sunday.
        with override_settings(ALLOW_BACKDATED_LEAVE=True, EMPLOYEE_WEEK_OFF_DAYS=[5, 6], EMPLOYEE_HOLIDAYS=['2026-10-06']):
            response = self.leave(start_date='2026-10-05', end_date='2026-10-11')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['calendar_days'], 7)
        self.assertEqual(response.data['working_days'], 4)

    def test_leave_history_scope_and_hr_department_filter(self):
        self.leave()
        self.api.force_authenticate(user=self.other)
        self.assertEqual(len(self.api.get('/api/leaves/').data), 0)
        self.assertEqual(self.api.get('/api/leaves/?view=all').status_code, 403)
        self.api.force_authenticate(user=self.hr)
        response = self.api.get('/api/leaves/', {'view': 'all', 'department': self.employee.profile.department_id, 'status': 'PENDING'})
        self.assertEqual(len(response.data), 1)

    def test_session_csrf_is_required_for_marking_and_leave_application(self):
        api = APIClient(enforce_csrf_checks=True)
        api.force_login(self.employee)
        self.assertEqual(api.post('/api/attendance/check-in/').status_code, 403)
        token = api.get('/api/profile/').data['csrf_token']
        self.assertEqual(api.post('/api/attendance/check-in/', HTTP_X_CSRFTOKEN=token).status_code, 201)
