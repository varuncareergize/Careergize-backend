from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from projects.models import Department


class MyProfileAPITests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='alice', password='test-password')
        self.other = get_user_model().objects.create_user(username='bob', password='test-password')
        self.other.profile.bank_account_number = 'private-bob-account'
        self.other.profile.save()
        self.client = APIClient(enforce_csrf_checks=True)

    def sign_in(self):
        response = self.client.post('/api/login/', {
            'username': 'alice', 'password': 'test-password',
        })
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/api/profile/')
        self.assertEqual(response.status_code, 200)
        return response.data['csrf_token']

    def test_anonymous_access_is_denied(self):
        self.assertEqual(self.client.get('/api/profile/').status_code, 403)
        self.assertEqual(self.client.patch('/api/profile/', {'address': 'test'}).status_code, 403)

    def test_update_own_profile_and_user_details(self):
        token = self.sign_in()
        department = Department.objects.create(name='IT')
        self.user.profile.department = department
        self.user.profile.save()
        response = self.client.patch('/api/profile/', {
            'first_name': 'Alice', 'email': 'alice@example.com',
            'phone_number': '+91 98765 43210', 'address': '12 Main Street',
            'department': department.pk, 'date_of_birth': '1995-04-10',
            'bank_account_number': '00123456789',
        }, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200, response.data)
        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Alice')
        self.assertEqual(self.user.profile.department_id, department.pk)
        self.assertEqual(self.user.profile.bank_account_number, '00123456789')
        self.assertEqual(self.client.get('/api/profile/').data['profile']['address'], '12 Main Street')

    def test_user_cannot_target_another_profile(self):
        token = self.sign_in()
        response = self.client.patch('/api/profile/', {
            'user': self.other.pk, 'username': 'bob', 'bank_account_number': 'alice-account',
        }, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.other.profile.refresh_from_db()
        self.assertEqual(self.other.profile.bank_account_number, 'private-bob-account')
        self.assertEqual(response.data['profile']['username'], 'alice')
        self.assertNotIn('private-bob-account', str(self.client.get('/api/profile/').data))

    def test_csrf_is_required_to_save(self):
        self.sign_in()
        self.assertEqual(self.client.patch('/api/profile/', {'address': 'test'}).status_code, 403)

    def test_invalid_fields_do_not_partially_save_user(self):
        token = self.sign_in()
        response = self.client.patch('/api/profile/', {
            'first_name': 'Should not save', 'phone_number': 'invalid',
            'date_of_birth': str(timezone.localdate() + timedelta(days=1)),
        }, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 400)
        self.assertIn('phone_number', response.data)
        self.assertIn('date_of_birth', response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, '')

    def test_logout_ends_session(self):
        token = self.sign_in()
        response = self.client.post('/api/logout/', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/profile/').status_code, 403)

    def test_general_users_api_excludes_private_profile_fields(self):
        self.sign_in()
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, 200)
        for user in response.data:
            self.assertNotIn('bank_account_number', user)
            self.assertNotIn('address', user)
