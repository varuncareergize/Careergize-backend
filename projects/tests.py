from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from .models import Client, Project, Team
from .serializers import ProjectSerializer


class ProjectAssignmentTests(TestCase):
    def test_api_saves_overview_and_multiple_assignees(self):
        from rest_framework.test import APIClient
        users = [get_user_model().objects.create_user(username=name) for name in ['manager', 'developer']]
        client = Client.objects.create(name='Overview Client')
        api = APIClient()
        admin_user = get_user_model().objects.create_user(username='project-admin', is_staff=True, is_superuser=True)
        api.force_authenticate(user=admin_user)
        payload = {
            'name': 'Client Portal', 'client': client.pk, 'project_type': 'Website',
            'status': 'Confirmed', 'priority': 'High', 'start_date': '2026-10-01',
            'expected_delivery_date': '2026-11-01', 'actual_delivery_date': None,
            'project_manager': users[0].pk, 'assigned_users': [user.pk for user in users],
            'progress': 25, 'website_url': 'https://example.com',
            'github_url': 'https://github.com/example/portal',
        }
        response = api.post('/api/projects/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        project = Project.objects.get(pk=response.data['id'])
        self.assertEqual(project.assigned_users.count(), 2)
        self.assertEqual(project.project_manager_id, users[0].pk)
        for value, _ in Project.STATUS_CHOICES:
            response = api.patch(f'/api/projects/{project.pk}/', {'status': value}, format='json')
            self.assertEqual(response.status_code, 200, response.data)
            project.refresh_from_db()
            self.assertEqual(project.status, value)
        response = api.patch(f'/api/projects/{project.pk}/', {'assigned_users': [users[1].pk]}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(project.assigned_users.values_list('pk', flat=True)), [users[1].pk])

    def test_overview_validation_rejects_invalid_values(self):
        client = Client.objects.create(name='Validation Client')
        serializer = ProjectSerializer(data={
            'name': 'Invalid dates', 'client': client.pk,
            'start_date': '2026-11-01', 'expected_delivery_date': '2026-10-01',
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('expected_delivery_date', serializer.errors)
        serializer = ProjectSerializer(data={
            'name': 'Invalid overview', 'client': client.pk,
            'status': 'Active', 'priority': 'Invalid', 'progress': 101,
            'assigned_users': [999999],
        })
        self.assertFalse(serializer.is_valid())
        for field in ['status', 'priority', 'progress', 'assigned_users']:
            self.assertIn(field, serializer.errors)

    def test_project_can_have_multiple_assigned_users(self):
        User = get_user_model()
        user_one = User.objects.create_user(username='alice', password='password123')
        user_two = User.objects.create_user(username='bob', password='password123')

        client = Client.objects.create(name='Acme Corp')
        team = Team.objects.create(name='Engineering')
        project = Project.objects.create(
            name='Website Redesign',
            client=client,
            team=team,
            expected_delivery_date='2026-12-31',
        )

        project.assigned_users.add(user_one, user_two)

        self.assertEqual(project.assigned_users.count(), 2)
        self.assertIn(user_one, project.assigned_users.all())
        self.assertIn(user_two, project.assigned_users.all())

    def test_project_serializer_includes_assigned_user_details(self):
        User = get_user_model()
        user = User.objects.create_user(username='carol', password='password123', first_name='Carol')

        client = Client.objects.create(name='Globex')
        team = Team.objects.create(name='Operations')
        project = Project.objects.create(
            name='Mobile App',
            client=client,
            team=team,
            expected_delivery_date='2026-10-15',
        )
        project.assigned_users.add(user)

        serializer = ProjectSerializer(project)

        self.assertEqual(serializer.data['assigned_user_details'][0]['username'], 'carol')
        self.assertEqual(serializer.data['assigned_user_details'][0]['first_name'], 'Carol')

    def test_project_calculates_amount_left(self):
        client = Client.objects.create(name='Beta Corp')
        team = Team.objects.create(name='Operations')
        project = Project.objects.create(
            name='Mobile App',
            client=client,
            team=team,
            expected_delivery_date='2026-11-30',
            total_amount=5000.00,
            amount_collected=3200.00,
        )

        self.assertEqual(project.amount_left, 1800.00)
