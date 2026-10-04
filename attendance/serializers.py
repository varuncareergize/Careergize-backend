from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from .models import Attendance, AttendanceAuditLog, LeaveRequest, LeaveAuditLog
from .services import company_timezone, today


class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.username', read_only=True)
    department = serializers.CharField(source='employee.profile.department.name', read_only=True, default=None)
    working_seconds = serializers.SerializerMethodField()

    def get_working_seconds(self, record):
        return int(record.working_hours.total_seconds())

    class Meta:
        model = Attendance
        fields = '__all__'
        read_only_fields = ['employee', 'date', 'check_in', 'check_out', 'working_hours', 'status', 'notes', 'created_at', 'updated_at']


class AttendanceCorrectionSerializer(serializers.Serializer):
    employee = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.filter(is_active=True))
    date = serializers.DateField()
    status = serializers.ChoiceField(choices=Attendance.Status.choices)
    check_in = serializers.DateTimeField(allow_null=True, required=False, default_timezone=company_timezone())
    check_out = serializers.DateTimeField(allow_null=True, required=False, default_timezone=company_timezone())
    notes = serializers.CharField(allow_blank=True, required=False)
    correction_reason = serializers.CharField()

    def validate(self, values):
        if values['date'] > today():
            raise serializers.ValidationError({'date': 'Attendance corrections cannot be dated in the future.'})
        for field in ['check_in', 'check_out']:
            timestamp = values.get(field)
            if timestamp and timestamp > timezone.now():
                raise serializers.ValidationError({field: 'Timestamps cannot be in the future.'})
        if values.get('check_in') and timezone.localtime(values['check_in'], company_timezone()).date() != values['date']:
            raise serializers.ValidationError({'check_in': 'Check in must belong to the selected attendance date.'})
        return values


class AttendanceAuditSerializer(serializers.ModelSerializer):
    corrected_by_name = serializers.CharField(source='corrected_by.username', read_only=True)
    class Meta:
        model = AttendanceAuditLog
        fields = '__all__'


class LeaveAuditSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.username', read_only=True)
    class Meta:
        model = LeaveAuditLog
        fields = ['id', 'actor_name', 'action', 'comment', 'created_at']


class LeaveSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.username', read_only=True)
    department = serializers.CharField(source='employee.profile.department.name', read_only=True, default=None)
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True, default=None)
    calendar_days = serializers.IntegerField(read_only=True)
    working_days = serializers.IntegerField(read_only=True)
    history = LeaveAuditSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = '__all__'
        read_only_fields = ['employee', 'status', 'applied_at', 'reviewed_at', 'reviewed_by', 'hr_comment', 'created_at', 'updated_at']


class LeaveReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['APPROVED', 'REJECTED'])
    hr_comment = serializers.CharField(allow_blank=True, required=False, default='')
