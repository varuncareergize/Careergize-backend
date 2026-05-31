from django.urls import path

from .views import (
    StudentDashboardAPIView,
    TaskAPIView,
    ScheduleAPIView,
    InstructorAPIView,
)

urlpatterns = [

    path(
        "dashboard/",
        StudentDashboardAPIView.as_view(),
        name="dashboard"
    ),

    path(
        "tasks/",
        TaskAPIView.as_view(),
        name="tasks"
    ),

    path(
        "schedules/",
        ScheduleAPIView.as_view(),
        name="schedules"
    ),

    path(
        "instructors/",
        InstructorAPIView.as_view(),
        name="instructors"
    ),
]