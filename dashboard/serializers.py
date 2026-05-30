# dashboard/serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone

from .models import (
    StudentProfile,
    Task,
    Instructor,
    Schedule
)


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
        return obj.first_name if obj.first_name else obj.username

    def get_program_name(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.program_name if profile else ""

    def get_modules_finished(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.modules_finished if profile else 0

    def get_total_modules(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.total_modules if profile else 0

    def get_attendance_rate(self, obj):
        profile = getattr(obj, 'profile', None)

        if profile:
            return float(profile.attendance_rate)

        return 0

    def get_pending_tasks_count(self, obj):
        return obj.tasks.filter(status="PENDING").count()

    def get_tasks(self, obj):
        pending_tasks = obj.tasks.filter(status="PENDING")
        return TaskSerializer(pending_tasks, many=True).data

    def get_next_session(self, obj):

        next_item = obj.schedules.filter(
            start_time__gte=timezone.now()
        ).order_by("start_time").first()

        if next_item:
            return {
                "title": next_item.title,
                "date": next_item.start_time.strftime("%B %d"),
                "time": next_item.start_time.strftime("%I:%M %p"),
                "instructor": (
                    next_item.instructor.name
                    if next_item.instructor
                    else "TBD"
                )
            }

        return None

    def get_weekly_schedule(self, obj):

        schedules = obj.schedules.filter(
            start_time__gte=timezone.now()
        ).order_by("start_time")[:5]

        data = []

        for item in schedules:

            delta = (
                item.start_time.date()
                - timezone.now().date()
            ).days

            if delta == 0:
                day_label = "TODAY"
            elif delta == 1:
                day_label = "TOMORROW"
            else:
                day_label = item.start_time.strftime(
                    "%B %d"
                ).upper()

            data.append({
                "id": item.id,
                "day_label": day_label,
                "title": item.title,
                "instructor": (
                    item.instructor.name
                    if item.instructor
                    else "TBD"
                ),
                "time_window": (
                    f"{item.start_time.strftime('%I:%M %p')} - "
                    f"{item.end_time.strftime('%I:%M %p')}"
                )
            })

        return data


class StudentProfileSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = [
            "id",
            "student_name",
            "program_name",
            "modules_finished",
            "total_modules",
            "attendance_rate",
            "user",
        ]

    def get_student_name(self, obj):
        return (
            obj.user.first_name if obj.user.first_name else obj.user.username
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