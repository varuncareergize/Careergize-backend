from rest_framework import serializers
from .models import Attendance


class AttendanceSerializer(serializers.ModelSerializer):

    schedule_name = serializers.CharField(
        source='schedule.title',
        read_only=True
    )

    student_username = serializers.CharField(
        source='student.username',
        read_only=True
    )

    class Meta:
        model = Attendance
        fields = '__all__'