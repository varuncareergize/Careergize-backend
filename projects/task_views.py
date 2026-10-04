from decimal import Decimal
from pathlib import PurePosixPath
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Project, Task, TaskDailyUpdate, TaskAttachment
from .task_permissions import is_hr_admin, can_manage_project, visible_tasks, manageable_projects
from .task_serializers import TaskSerializer, DailyUpdateSerializer, CommentSerializer, AttachmentSerializer
from .task_services import refresh_project_progress, apply_daily_update


class TaskAccessView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def task(self, request, pk, lock=False):
        queryset = visible_tasks(request.user)
        if lock:
            queryset = queryset.select_for_update()
        return get_object_or_404(queryset, pk=pk)


class TaskListView(TaskAccessView):
    def get(self, request):
        tasks = visible_tasks(request.user)
        if request.query_params.get('include_archived') != 'true':
            tasks = tasks.filter(is_active=True)
        project = request.query_params.get('project')
        if project:
            if not project.isdigit():
                raise ValidationError({'project': 'Enter a valid project ID.'})
            tasks = tasks.filter(project_id=project)
        if request.query_params.get('status'):
            tasks = tasks.filter(status=request.query_params['status'])
        if request.query_params.get('assigned_to'):
            assignee = request.query_params['assigned_to']
            if not assignee.isdigit():
                raise ValidationError({'assigned_to': 'Enter a valid employee ID.'})
            tasks = tasks.filter(assigned_to_id=assignee)
        return Response(TaskSerializer(tasks, many=True, context={'request': request}).data)

    @transaction.atomic
    def post(self, request):
        serializer = TaskSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        project = serializer.validated_data['project']
        if not can_manage_project(request.user, project):
            raise PermissionDenied('Only HR/admin or this project manager can create tasks.')
        if not project.is_active:
            raise ValidationError({'project': 'This project is archived.'})
        assignee = serializer.validated_data['assigned_to']
        if not assignee.is_active:
            raise ValidationError({'assigned_to': 'Choose an active employee.'})
        if not is_hr_admin(request.user) and not project.assigned_users.filter(pk=assignee.pk).exists():
            raise ValidationError({'assigned_to': 'Assign tasks to a member of this project.'})
        task = serializer.save(created_by=request.user)
        refresh_project_progress(task.project_id)
        return Response(TaskSerializer(task, context={'request': request}).data, status=201)


class TaskDetailView(TaskAccessView):
    def get(self, request, pk):
        return Response(TaskSerializer(self.task(request, pk), context={'request': request}).data)

    @transaction.atomic
    def patch(self, request, pk):
        task = self.task(request, pk, lock=True)
        if not can_manage_project(request.user, task.project):
            raise PermissionDenied('Employees update tasks through daily work updates.')
        old_project_id = task.project_id
        serializer = TaskSerializer(task, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        project = serializer.validated_data.get('project', task.project)
        if not can_manage_project(request.user, project):
            raise PermissionDenied("You cannot move a task to another manager's project.")
        if not project.is_active:
            raise ValidationError({'project': 'This project is archived.'})
        assignee = serializer.validated_data.get('assigned_to', task.assigned_to)
        if not assignee.is_active:
            raise ValidationError({'assigned_to': 'Choose an active employee.'})
        if not is_hr_admin(request.user) and not project.assigned_users.filter(pk=assignee.pk).exists():
            raise ValidationError({'assigned_to': 'Assign tasks to a member of this project.'})
        serializer.save()
        refresh_project_progress(old_project_id)
        if old_project_id != project.pk:
            refresh_project_progress(project.pk)
        return Response(serializer.data)


    @transaction.atomic
    def delete(self, request, pk):
        task = self.task(request, pk, lock=True)
        if not can_manage_project(request.user, task.project):
            raise PermissionDenied('Only HR/admin or this project manager can delete tasks.')
        task.is_active = False
        task.save()
        refresh_project_progress(task.project_id)
        return Response(status=204)


class TaskDailyUpdateView(TaskAccessView):
    def get(self, request, pk):
        task = self.task(request, pk)
        return Response(DailyUpdateSerializer(task.daily_updates.select_related('employee'), many=True).data)

    @transaction.atomic
    def post(self, request, pk):
        task = self.task(request, pk, lock=True)
        if task.assigned_to_id != request.user.pk:
            raise PermissionDenied('Only the assigned employee can submit daily work.')
        if not task.is_active or task.status in ['COMPLETED', 'CANCELLED']:
            raise ValidationError({'task': 'This task is closed. Ask a manager to reopen it.'})
        serializer = DailyUpdateSerializer(data=request.data, context={'task': task})
        serializer.is_valid(raise_exception=True)
        # Serialize same-employee submissions across tasks to enforce a daily hour limit.
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        values = serializer.validated_data
        total = TaskDailyUpdate.objects.filter(employee=request.user, work_date=values['work_date']).aggregate(value=Sum('hours_worked'))['value'] or Decimal('0')
        if total + values['hours_worked'] > 24:
            raise ValidationError({'hours_worked': 'Total logged work for this date cannot exceed 24 hours.'})
        update = serializer.save(task=task, employee=request.user)
        apply_daily_update(task)
        return Response(DailyUpdateSerializer(update).data, status=201)


class TaskCommentView(TaskAccessView):
    def get(self, request, pk):
        task = self.task(request, pk)
        return Response(CommentSerializer(task.comments.select_related('user'), many=True).data)

    def post(self, request, pk):
        task = self.task(request, pk)
        serializer = CommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(task=task, user=request.user)
        return Response(serializer.data, status=201)


class TaskAttachmentView(TaskAccessView):
    def get(self, request, pk):
        task = self.task(request, pk)
        return Response(AttachmentSerializer(task.attachments.select_related('uploaded_by'), many=True).data)

    def post(self, request, pk):
        task = self.task(request, pk)
        if not task.is_active:
            raise ValidationError({'task': 'This task is archived.'})
        serializer = AttachmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file = serializer.validated_data['file']
        name = PurePosixPath(file.name.replace(chr(92), '/')).name
        serializer.save(task=task, uploaded_by=request.user, file_name=name)
        return Response(serializer.data, status=201)


class TaskAttachmentDownloadView(TaskAccessView):
    def get(self, request, pk, attachment_pk):
        task = self.task(request, pk)
        attachment = get_object_or_404(TaskAttachment, pk=attachment_pk, task=task)
        response = FileResponse(attachment.file.open('rb'), as_attachment=True, filename=attachment.file_name, content_type='application/octet-stream')
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'private, no-store'
        return response


class TaskOptionsView(TaskAccessView):
    def get(self, request):
        projects = Project.objects.all() if is_hr_admin(request.user) else Project.objects.filter(Q(project_manager=request.user) | Q(assigned_users=request.user) | Q(tasks__assigned_to=request.user)).distinct()
        projects = projects.filter(is_active=True)
        items = []
        for project in projects:
            tasks = project.tasks.filter(is_active=True).exclude(status='CANCELLED')
            members = list(project.assigned_users.values_list('pk', flat=True))
            totals = tasks.aggregate(estimated=Sum('estimated_hours'), actual=Sum('actual_hours'))
            items.append({
                'id': project.pk, 'name': project.name, 'can_manage': can_manage_project(request.user, project),
                'assigned_users': members, 'progress': project.progress,
                'task_count': tasks.count(), 'completed_tasks': tasks.filter(status='COMPLETED').count(),
                'blocked_tasks': tasks.filter(status='BLOCKED').count(),
                'estimated_hours': totals['estimated'] or 0, 'actual_hours': totals['actual'] or 0,
            })
        # Employees receive no unnecessary user directory from this endpoint.
        users = get_user_model().objects.filter(is_active=True) if manageable_projects(request.user).exists() or is_hr_admin(request.user) else get_user_model().objects.filter(pk=request.user.pk)
        return Response({'projects': items, 'users': list(users.values('id', 'username', 'first_name', 'last_name')), 'is_hr_admin': is_hr_admin(request.user)})
