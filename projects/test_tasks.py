import tempfile
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Client, Department, Project, Task, TaskDailyUpdate, TaskAttachment


class TaskWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='admin', is_staff=True, is_superuser=True)
        self.hr = User.objects.create_user(username='hr')
        self.hr.profile.department = Department.objects.create(name='HR')
        self.hr.profile.save()
        self.manager = User.objects.create_user(username='manager')
        self.other_manager = User.objects.create_user(username='other-manager')
        self.employee = User.objects.create_user(username='employee')
        self.other_employee = User.objects.create_user(username='other-employee')
        self.outsider = User.objects.create_user(username='outsider')
        client = Client.objects.create(name='Task client')
        self.project = Project.objects.create(name='Payment project', client=client, project_manager=self.manager)
        self.project.assigned_users.add(self.employee, self.other_employee)
        self.other_project = Project.objects.create(name='Other project', client=client, project_manager=self.other_manager)
        self.other_project.assigned_users.add(self.other_employee)
        self.task = Task.objects.create(
            project=self.project, title='Implement Payment Gateway', assigned_to=self.employee,
            created_by=self.manager, start_date=timezone.localdate() - timedelta(days=10), estimated_hours=20,
        )
        self.other_task = Task.objects.create(project=self.other_project, title='Private task', assigned_to=self.other_employee, created_by=self.other_manager)
        self.api = APIClient()

    def actor(self, user):
        self.api.force_authenticate(user=user)

    def update(self, **values):
        payload = {
            'work_date': str(timezone.localdate()), 'work_description': 'Implemented checkout',
            'hours_worked': '5.00', 'progress_percentage': 30, 'status': 'IN_PROGRESS',
        }
        payload.update(values)
        return self.api.post(f'/api/tasks/{self.task.pk}/updates/', payload, format='json')

    def test_anonymous_access_is_denied(self):
        self.assertEqual(self.api.get('/api/tasks/').status_code, 403)
        self.assertEqual(self.api.get('/api/task-options/').status_code, 403)

    def test_task_visibility_for_roles_and_project_boundaries(self):
        for user, expected in [(self.admin, 2), (self.hr, 2), (self.manager, 1), (self.employee, 1), (self.outsider, 0)]:
            self.actor(user)
            response = self.api.get('/api/tasks/')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data), expected)
        self.actor(self.employee)
        for suffix in ['', 'updates/', 'comments/', 'attachments/']:
            self.assertEqual(self.api.get(f'/api/tasks/{self.other_task.pk}/{suffix}').status_code, 404)

    def test_manager_and_hr_create_and_reassign_tasks(self):
        for user in [self.hr, self.admin, self.manager]:
            self.actor(user)
            response = self.api.post('/api/tasks/', {
                'project': self.project.pk, 'title': f'Task by {user.username}',
                'assigned_to': self.employee.pk, 'created_by': self.outsider.pk,
                'priority': 'HIGH', 'estimated_hours': '12.50',
            }, format='json')
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(response.data['created_by'], user.pk)
        self.actor(self.manager)
        response = self.api.patch(f'/api/tasks/{self.task.pk}/', {'assigned_to': self.other_employee.pk, 'due_date': str(timezone.localdate() + timedelta(days=2)), 'priority': 'URGENT'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.assigned_to_id, self.other_employee.pk)
        self.assertEqual(self.task.priority, 'URGENT')

    def test_manager_cannot_create_or_move_tasks_to_other_projects(self):
        self.actor(self.manager)
        response = self.api.post('/api/tasks/', {'project': self.other_project.pk, 'title': 'No access', 'assigned_to': self.other_employee.pk}, format='json')
        self.assertEqual(response.status_code, 403)
        response = self.api.patch(f'/api/tasks/{self.task.pk}/', {'project': self.other_project.pk}, format='json')
        self.assertEqual(response.status_code, 403)
        response = self.api.patch(f'/api/tasks/{self.task.pk}/', {'assigned_to': self.outsider.pk}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_employee_cannot_create_edit_delete_or_promote_self(self):
        self.actor(self.employee)
        self.assertEqual(self.api.post('/api/tasks/', {'project': self.project.pk, 'title': 'Forbidden', 'assigned_to': self.employee.pk}, format='json').status_code, 403)
        self.assertEqual(self.api.patch(f'/api/tasks/{self.task.pk}/', {'description': 'Changed', 'assigned_to': self.outsider.pk, 'estimated_hours': 500}, format='json').status_code, 403)
        self.assertEqual(self.api.delete(f'/api/tasks/{self.task.pk}/').status_code, 403)
        self.assertEqual(self.api.patch(f'/api/projects/{self.project.pk}/', {'project_manager': self.employee.pk}, format='json').status_code, 403)
        response = self.api.patch('/api/profile/', {'department': self.hr.profile.department_id}, format='json')
        self.assertEqual(response.status_code, 200)
        self.employee.profile.refresh_from_db()
        self.assertIsNone(self.employee.profile.department_id)
        self.assertEqual(self.api.patch(f'/api/tasks/{self.task.pk}/', {'priority': 'URGENT'}, format='json').status_code, 403)

    def test_daily_history_hours_and_project_progress_roll_up(self):
        self.actor(self.employee)
        second = Task.objects.create(project=self.project, title='Second task', assigned_to=self.employee, created_by=self.manager)
        for days, hours, progress in [(3, '5', 30), (2, '6', 55), (1, '7', 80), (0, '5', 100)]:
            response = self.update(work_date=str(timezone.localdate() - timedelta(days=days)), hours_worked=hours, progress_percentage=progress, status='COMPLETED' if progress == 100 else 'IN_PROGRESS')
            self.assertEqual(response.status_code, 201, response.data)
        self.task.refresh_from_db()
        self.project.refresh_from_db()
        self.assertEqual(self.task.daily_updates.count(), 4)
        self.assertEqual(self.task.actual_hours, Decimal('23'))
        self.assertEqual(self.task.progress_percentage, 100)
        self.assertEqual(self.task.status, 'IN_REVIEW')
        self.assertIsNone(self.task.completed_at)
        self.assertEqual(self.project.progress, 50)
        self.actor(self.manager)
        response = self.api.patch(f'/api/tasks/{self.task.pk}/', {'status': 'COMPLETED'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertIsNotNone(self.task.completed_at)
        self.actor(self.employee)
        self.assertEqual(self.update().status_code, 400)

    def test_backdated_update_adds_hours_without_replacing_latest_progress(self):
        self.actor(self.employee)
        self.assertEqual(self.update(progress_percentage=80).status_code, 201)
        self.assertEqual(self.update(work_date=str(timezone.localdate() - timedelta(days=2)), hours_worked='2', progress_percentage=20).status_code, 201)
        self.task.refresh_from_db()
        self.assertEqual(self.task.progress_percentage, 80)
        self.assertEqual(self.task.actual_hours, Decimal('7'))
        self.assertEqual(self.task.daily_updates.count(), 2)

    def test_only_assignee_can_log_work_and_history_has_no_edit_delete_endpoints(self):
        self.actor(self.manager)
        self.assertEqual(self.update().status_code, 403)
        self.actor(self.other_employee)
        self.assertEqual(self.update().status_code, 404)
        self.actor(self.employee)
        response = self.update(employee=self.outsider.pk, task=self.other_task.pk)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['employee'], self.employee.pk)
        self.assertEqual(response.data['task'], self.task.pk)
        self.assertEqual(self.api.patch(f'/api/tasks/{self.task.pk}/updates/', {}, format='json').status_code, 405)
        self.assertEqual(self.api.delete(f'/api/tasks/{self.task.pk}/updates/').status_code, 405)

    def test_work_validation_and_daily_hour_limit(self):
        self.actor(self.employee)
        for values in [
            {'hours_worked': '-1'}, {'hours_worked': '25'}, {'progress_percentage': 101},
            {'work_date': str(timezone.localdate() + timedelta(days=1))},
            {'work_date': str(self.task.start_date - timedelta(days=1))},
            {'status': 'CANCELLED'}, {'status': 'COMPLETED', 'progress_percentage': 90},
        ]:
            self.assertEqual(self.update(**values).status_code, 400, values)
        self.assertEqual(self.update(hours_worked='23').status_code, 201)
        self.assertEqual(self.update(hours_worked='2').status_code, 400)
        self.assertEqual(self.task.daily_updates.count(), 1)

    def test_default_update_status_and_blockers(self):
        self.actor(self.employee)
        response = self.api.post(f'/api/tasks/{self.task.pk}/updates/', {
            'work_date': str(timezone.localdate()), 'work_description': 'Configuration',
            'hours_worked': 0, 'progress_percentage': 0, 'blockers': 'Awaiting credentials',
            'next_plan': 'Test checkout', 'employee_comment': 'Please share access',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['status'], 'IN_PROGRESS')
        self.assertEqual(response.data['blockers'], 'Awaiting credentials')

    def test_comments_are_owned_and_scoped(self):
        for actor in [self.employee, self.manager, self.hr]:
            self.actor(actor)
            response = self.api.post(f'/api/tasks/{self.task.pk}/comments/', {'comment': 'Please review', 'user': self.outsider.pk}, format='json')
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.data['user'], actor.pk)
        self.actor(self.outsider)
        self.assertEqual(self.api.post(f'/api/tasks/{self.task.pk}/comments/', {'comment': 'No access'}, format='json').status_code, 404)

    def test_upload_and_download_require_task_access(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            self.actor(self.employee)
            response = self.api.post(f'/api/tasks/{self.task.pk}/attachments/', {
                'file': SimpleUploadedFile('test-report.txt', b'Test report'), 'description': 'Checkout test results',
                'uploaded_by': self.outsider.pk,
            }, format='multipart')
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(response.data['uploaded_by'], self.employee.pk)
            self.assertNotIn('file', response.data)
            attachment = TaskAttachment.objects.get(pk=response.data['id'])
            self.assertNotEqual(attachment.file.name, attachment.file_name)
            url = response.data['download_url']
            response = self.api.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b''.join(response.streaming_content), b'Test report')
            self.actor(self.outsider)
            self.assertEqual(self.api.get(url).status_code, 404)
            self.actor(self.employee)
            self.assertEqual(self.api.post(f'/api/tasks/{self.task.pk}/attachments/', {'file': SimpleUploadedFile('empty.txt', b'')}, format='multipart').status_code, 400)

    def test_archive_preserves_history_and_excludes_progress(self):
        self.actor(self.employee)
        self.update(progress_percentage=60)
        self.actor(self.manager)
        response = self.api.patch(f'/api/tasks/{self.task.pk}/', {'is_active': False}, format='json')
        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()
        self.assertEqual(self.project.progress, 0)
        self.assertEqual(len(self.api.get('/api/tasks/').data), 0)
        self.assertEqual(len(self.api.get('/api/tasks/?include_archived=true').data), 1)
        self.assertEqual(len(self.api.get(f'/api/tasks/{self.task.pk}/updates/').data), 1)
        self.actor(self.employee)
        self.assertEqual(self.update().status_code, 400)

    def test_task_dates_hours_progress_and_choices_are_validated(self):
        self.actor(self.manager)
        response = self.api.patch(f'/api/tasks/{self.task.pk}/', {
            'start_date': '2026-10-10', 'due_date': '2026-10-01',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        for values in [{'estimated_hours': '-2'}, {'progress_percentage': 101}, {'status': 'INVALID'}, {'priority': 'INVALID'}]:
            self.assertEqual(self.api.patch(f'/api/tasks/{self.task.pk}/', values, format='json').status_code, 400)
        for values in [{'progress_percentage': 101}, {'actual_hours': -1}, {'estimated_hours': -1}]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Task.objects.filter(pk=self.task.pk).update(**values)

    def test_logged_hours_and_creator_cannot_be_overwritten(self):
        self.actor(self.employee)
        self.update()
        self.actor(self.manager)
        response = self.api.patch(f'/api/tasks/{self.task.pk}/', {'actual_hours': 999, 'created_by': self.outsider.pk}, format='json')
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.created_by_id, self.manager.pk)
        self.assertEqual(self.task.actual_hours, Decimal('5'))

    def test_session_authentication_enforces_csrf(self):
        api = APIClient(enforce_csrf_checks=True)
        api.force_login(self.employee)
        response = api.post(f'/api/tasks/{self.task.pk}/comments/', {'comment': 'No CSRF'}, format='json')
        self.assertEqual(response.status_code, 403)
        token = api.get('/api/profile/').data['csrf_token']
        response = api.post(f'/api/tasks/{self.task.pk}/comments/', {'comment': 'With CSRF'}, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 201)

    def test_project_summary_is_scoped(self):
        self.actor(self.employee)
        self.update(progress_percentage=55)
        response = self.api.get('/api/task-options/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([project['id'] for project in response.data['projects']], [self.project.pk])
        summary = response.data['projects'][0]
        self.assertEqual(summary['progress'], 55)
        self.assertEqual(summary['actual_hours'], Decimal('5'))
        self.assertFalse(summary['can_manage'])

    def test_login_capabilities_follow_department_and_manager_assignment(self):
        for user, role, create in [(self.hr, 'HR/Admin', True), (self.manager, 'Manager', True), (self.employee, 'Employee', False)]:
            self.actor(user)
            capabilities = self.api.get('/api/profile/').data['capabilities']
            self.assertEqual(capabilities['role'], role)
            self.assertEqual(capabilities['can_create_project'], create)
            self.assertEqual(capabilities['can_delete'], create)

    def test_manager_department_can_create_own_project(self):
        user = get_user_model().objects.create_user(username='department-manager')
        user.profile.department = Department.objects.create(name='Manager')
        user.profile.save()
        self.actor(user)
        self.assertTrue(self.api.get('/api/profile/').data['capabilities']['can_create_project'])
        response = self.api.post('/api/projects/', {
            'name': 'New managed project', 'client': self.project.client_id,
            'project_manager': self.outsider.pk, 'assigned_users': [self.employee.pk],
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['project_manager'], user.pk)
        self.assertTrue(response.data['can_manage'])

    def test_hr_manager_delete_preserves_task_and_daily_history(self):
        self.actor(self.employee)
        self.update()
        self.actor(self.manager)
        response = self.api.delete(f'/api/tasks/{self.task.pk}/')
        self.assertEqual(response.status_code, 204)
        self.task.refresh_from_db()
        self.assertFalse(self.task.is_active)
        self.assertEqual(self.task.daily_updates.count(), 1)
        self.assertEqual(self.api.delete(f'/api/projects/{self.other_project.pk}/').status_code, 404)
        response = self.api.delete(f'/api/projects/{self.project.pk}/')
        self.assertEqual(response.status_code, 204)
        self.project.refresh_from_db()
        self.assertFalse(self.project.is_active)
        self.assertEqual(self.task.daily_updates.count(), 1)
        self.assertEqual(len(self.api.get('/api/projects/').data), 0)

    def test_it_role_cannot_create_delete_or_edit_project_structure(self):
        self.employee.profile.department = Department.objects.create(name='IT')
        self.employee.profile.save()
        self.actor(self.employee)
        capabilities = self.api.get('/api/profile/').data['capabilities']
        self.assertEqual(capabilities['department'], 'IT')
        self.assertFalse(capabilities['can_create_project'])
        response = self.api.post('/api/projects/', {'name': 'Forbidden project', 'client': self.project.client_id}, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.api.delete(f'/api/projects/{self.project.pk}/').status_code, 403)
        self.assertEqual(self.api.delete(f'/api/tasks/{self.task.pk}/').status_code, 403)
        response = self.api.get('/api/projects/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data[0]['can_manage'])
        self.assertEqual(self.update().status_code, 201)

    def test_it_department_overrides_staff_groups_and_project_manager_assignment(self):
        from django.contrib.auth.models import Group
        self.employee.profile.department = Department.objects.create(name='IT')
        self.employee.profile.save()
        self.employee.is_staff = True
        self.employee.is_superuser = True
        self.employee.save()
        self.employee.groups.add(Group.objects.create(name='Manager'), Group.objects.create(name='HR'))
        self.project.project_manager = self.employee
        self.project.save()
        self.actor(self.employee)
        capabilities = self.api.get('/api/profile/').data['capabilities']
        self.assertEqual(capabilities['role'], 'Employee')
        for field in ['can_create_project', 'can_create_task', 'can_delete', 'is_hr_admin']:
            self.assertFalse(capabilities[field])
        options = self.api.get('/api/task-options/').data
        self.assertTrue(options['projects'])
        self.assertFalse(any(project['can_manage'] for project in options['projects']))
        self.assertFalse(self.api.get(f'/api/tasks/{self.task.pk}/').data['can_manage'])
        self.assertEqual(self.api.post('/api/projects/', {'name': 'Forbidden', 'client': self.project.client_id}, format='json').status_code, 403)
        self.assertEqual(self.api.post('/api/tasks/', {'project': self.project.pk, 'title': 'Forbidden', 'assigned_to': self.employee.pk}, format='json').status_code, 403)
        self.assertEqual(self.api.delete(f'/api/tasks/{self.task.pk}/').status_code, 403)
        self.assertEqual(self.update().status_code, 201)

    def test_staff_without_hr_department_is_not_an_admin(self):
        user = get_user_model().objects.create_user(username='ordinary-staff', is_staff=True)
        self.actor(user)
        capabilities = self.api.get('/api/profile/').data['capabilities']
        self.assertFalse(capabilities['can_create_project'])
        self.assertFalse(capabilities['can_create_task'])
        self.assertFalse(capabilities['is_hr_admin'])
