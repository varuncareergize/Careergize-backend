from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone

from .models import (
    StudentProfile,
    Task,
    Instructor,
    Schedule
)


class TaskSerializer(serializers.ModelSerializer):

    class Meta:
        model = Task
        fields = "__all__"


class InstructorSerializer(serializers.ModelSerializer):

    class Meta:
        model = Instructor
        fields = "__all__"


class ScheduleSerializer(serializers.ModelSerializer):

    instructor_name = serializers.CharField(
        source="instructor.name",
        read_only=True
    )

    class Meta:
        model = Schedule
        fields = "__all__"


class StudentProfileSerializer(serializers.ModelSerializer):

    student_name = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = "__all__"

    def get_student_name(self, obj):
        return obj.user.first_name or obj.user.username


class DashboardSerializer(serializers.ModelSerializer):

    student_name = serializers.SerializerMethodField()
    program_name = serializers.SerializerMethodField()
    modules_finished = serializers.SerializerMethodField()
    total_modules = serializers.SerializerMethodField()
    attendance_rate = serializers.SerializerMethodField()

    pending_tasks_count = serializers.SerializerMethodField()
    tasks = serializers.SerializerMethodField()

    next_session = serializers.SerializerMethodField()
    weekly_schedule = serializers.SerializerMethodField()

    class Meta:
        model = User

        fields = [
            "student_name",
            "program_name",
            "modules_finished",
            "total_modules",
            "attendance_rate",
            "pending_tasks_count",
            "tasks",
            "next_session",
            "weekly_schedule",
        ]

    def get_student_name(self, obj):
        return obj.first_name or obj.username

    def get_program_name(self, obj):

        try:
            return obj.profile.program_name
        except:
            return ""

    def get_modules_finished(self, obj):

        try:
            return obj.profile.modules_finished
        except:
            return 0

    def get_total_modules(self, obj):

        try:
            return obj.profile.total_modules
        except:
            return 0

    def get_attendance_rate(self, obj):

        try:
            return float(obj.profile.attendance_rate)
        except:
            return 0

    def get_pending_tasks_count(self, obj):

        return Task.objects.filter(
            student=obj,
            status="PENDING"
        ).count()

    def get_tasks(self, obj):

        tasks = Task.objects.filter(
            student=obj,
            status="PENDING"
        )

        return TaskSerializer(
            tasks,
            many=True
        ).data

    def get_next_session(self, obj):

        next_schedule = Schedule.objects.filter(
            student=obj,
            start_time__gte=timezone.now()
        ).order_by("start_time").first()

        if not next_schedule:
            return None

        return {
            "title": next_schedule.title,
            "date": next_schedule.start_time.strftime("%d %b %Y"),
            "time": next_schedule.start_time.strftime("%I:%M %p"),
            "instructor": (
                next_schedule.instructor.name
                if next_schedule.instructor
                else "N/A"
            )
        }

    def get_weekly_schedule(self, obj):

        schedules = Schedule.objects.filter(
            student=obj
        ).order_by("start_time")[:5]

        return ScheduleSerializer(
            schedules,
            many=True
        ).data