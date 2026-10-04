from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from .models import Task, TaskDailyUpdate, TaskComment, TaskAttachment


class TaskSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    can_manage = serializers.SerializerMethodField()
    can_update = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['created_by', 'actual_hours', 'completed_at', 'created_at', 'updated_at']

    def get_can_manage(self, task):
        from .task_permissions import can_manage_project
        return can_manage_project(self.context['request'].user, task.project)

    def get_can_update(self, task):
        return task.is_active and task.assigned_to_id == self.context['request'].user.pk and task.status not in ['COMPLETED', 'CANCELLED']

    def validate(self, attrs):
        start = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        due = attrs.get('due_date', getattr(self.instance, 'due_date', None))
        if start and due and due < start:
            raise serializers.ValidationError({'due_date': 'Due date cannot be before start date.'})
        if attrs.get('status') == 'COMPLETED':
            attrs['progress_percentage'] = 100
        return attrs


class DailyUpdateSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.username', read_only=True)

    class Meta:
        model = TaskDailyUpdate
        fields = '__all__'
        read_only_fields = ['task', 'employee', 'created_at', 'updated_at']

    def validate(self, attrs):
        date = attrs['work_date']
        task = self.context['task']
        if date > timezone.localdate():
            raise serializers.ValidationError({'work_date': 'Work date cannot be in the future.'})
        if task.start_date and date < task.start_date:
            raise serializers.ValidationError({'work_date': 'Work date cannot be before task start date.'})
        if attrs.get('status', 'IN_PROGRESS') == 'CANCELLED':
            raise serializers.ValidationError({'status': 'Only managers can cancel tasks.'})
        if attrs.get('status', 'IN_PROGRESS') == 'COMPLETED' and attrs['progress_percentage'] != 100:
            raise serializers.ValidationError({'progress_percentage': 'A completion submission must have 100% progress.'})
        return attrs


class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = TaskComment
        fields = '__all__'
        read_only_fields = ['task', 'user', 'created_at', 'updated_at']


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = TaskAttachment
        fields = ['id', 'task', 'uploaded_by', 'uploaded_by_name', 'file', 'file_name', 'description', 'created_at', 'download_url']
        read_only_fields = ['task', 'uploaded_by', 'file_name', 'created_at']
        extra_kwargs = {'file': {'write_only': True}}

    def get_download_url(self, attachment):
        return f'/api/tasks/{attachment.task_id}/attachments/{attachment.pk}/download/'

    def validate_file(self, file):
        if not file.size or file.size > 20 * 1024 * 1024:
            raise serializers.ValidationError('Upload a nonempty file of up to 20 MB.')
        if len(file.name) > 255:
            raise serializers.ValidationError('File name must not exceed 255 characters.')
        return file
