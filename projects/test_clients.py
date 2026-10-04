from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Client, Project


class ClientDetailsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='salesperson')
        self.api = APIClient(enforce_csrf_checks=True)
        self.api.force_login(self.user)
        self.token = self.api.get('/api/profile/').data['csrf_token']

    def test_create_and_edit_all_client_details(self):
        payload = {
            'name': 'ABC Technologies', 'contact_person': 'John Mathew',
            'email': 'john@abc.com', 'phone': '+91 98765 43210',
            'whatsapp_number': '+91 98765 43210', 'address': 'Bangalore, Karnataka',
            'industry': 'IT / Software', 'client_type': 'Company', 'source': 'Referral',
            'assigned_to': self.user.pk, 'status': 'Lead', 'notes': 'General client information',
        }
        response = self.api.post('/api/clients/', payload, format='json', HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 201, response.data)
        client = Client.objects.get(pk=response.data['id'])
        for field, value in payload.items():
            self.assertEqual(getattr(client, f'{field}_id' if field == 'assigned_to' else field), value)
        self.assertEqual(response.data['assigned_to_name'], 'salesperson')
        project = Project.objects.create(name='Linked project', client=client)
        response = self.api.patch(f'/api/clients/{client.pk}/', {
            'name': 'ABC Updated', 'status': 'Active', 'client_type': 'Individual',
            'source': 'LinkedIn', 'assigned_to': None,
        }, format='json', HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 200, response.data)
        response = self.api.get(f'/api/clients/{client.pk}/')
        self.assertEqual(response.data['name'], 'ABC Updated')
        self.assertEqual(response.data['status'], 'Active')
        self.assertIsNone(response.data['assigned_to'])
        project.refresh_from_db()
        self.assertEqual(project.client_id, client.pk)

    def test_invalid_fields_and_duplicate_name_are_rejected(self):
        response = self.api.post('/api/clients/', {
            'name': 'Invalid', 'email': 'not-email', 'phone': 'invalid',
            'whatsapp_number': 'invalid', 'status': 'Unknown', 'client_type': 'Unknown',
            'assigned_to': 999999,
        }, format='json', HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 400)
        for field in ['email', 'phone', 'whatsapp_number', 'status', 'client_type', 'assigned_to']:
            self.assertIn(field, response.data)
        Client.objects.create(name='Existing')
        response = self.api.post('/api/clients/', {'name': 'Existing'}, format='json', HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 400)
        self.assertIn('name', response.data)

    def test_assigned_user_deletion_preserves_client(self):
        client = Client.objects.create(name='Keep client', assigned_to=self.user)
        self.user.delete()
        client.refresh_from_db()
        self.assertIsNone(client.assigned_to_id)
