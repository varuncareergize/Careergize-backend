from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from .models import Client, Project, Team
from .serializers import ProjectSerializer


class ProjectAssignmentTests(TestCase):
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
            delivery_date='2026-12-31',
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
            delivery_date='2026-10-15',
        )
        project.assigned_users.add(user)

        serializer = ProjectSerializer(project)

        self.assertEqual(serializer.data['assigned_users'][0]['username'], 'carol')
        self.assertEqual(serializer.data['assigned_users'][0]['first_name'], 'Carol')

    def test_project_calculates_amount_left(self):
        client = Client.objects.create(name='Beta Corp')
        team = Team.objects.create(name='Operations')
        project = Project.objects.create(
            name='Mobile App',
            client=client,
            team=team,
            delivery_date='2026-11-30',
            total_amount=5000.00,
            amount_collected=3200.00,
        )

        self.assertEqual(project.amount_left, 1800.00)
