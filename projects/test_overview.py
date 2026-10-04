from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from attendance.models import Attendance
from attendance.services import today
from .models import Department


class OverviewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='employee', is_staff=True)
        self.user.profile.department = Department.objects.create(name='IT')
        self.user.profile.save()
        self.hr = get_user_model().objects.create_user(username='hr')
        self.hr.profile.department = Department.objects.create(name='HR')
        self.hr.profile.save()
        self.api = APIClient()

    def test_authentication_and_employee_scope(self):
        self.assertEqual(self.api.get('/api/overview/').status_code, 403)
        self.api.force_authenticate(self.user)
        response = self.api.get('/api/overview/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([m['id'] for m in response.data['members']], [self.user.pk])
        self.assertEqual(response.data['summary']['absent'], 1)
        self.assertEqual(len(response.data['activity']), 7)
        self.assertFalse(Attendance.objects.exists())
        self.assertEqual(self.api.get('/api/overview/?date=invalid').status_code, 400)

    def test_hr_counts_and_explicit_status_preserved(self):
        self.api.force_authenticate(self.hr)
        Attendance.objects.create(employee=self.user, date=today(), status='PRESENT')
        response = self.api.get('/api/overview/')
        self.assertEqual(response.data['summary']['present'], 1)
        self.assertEqual(response.data['summary']['absent'], 1)
        Attendance.objects.create(employee=self.hr, date=today(), status='HOLIDAY')
        response = self.api.get('/api/overview/')
        self.assertEqual(response.data['summary']['absent'], 0)
        self.assertIn('HOLIDAY', [m['status'] for m in response.data['members']])
