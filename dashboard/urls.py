    # dashboard/urls.py
from django.urls import path
from .views import (
    StudentProfileAPIView,
    TaskAPIView,
    InstructorAPIView,
    ScheduleAPIView,
    StudentDashboardAPIView
    # LoginAPIView
)

urlpatterns = [
    path('dashboard/', StudentDashboardAPIView.as_view(), name='student-dashboard'),
    # path('login/', LoginAPIView.as_view(), name='login'),
        path(
        'student-profile/',
        StudentProfileAPIView.as_view(),
        name='student-profile-create'
    ),
    path(
        'student-profile/<int:pk>/',
        StudentProfileAPIView.as_view(),
        name='student-profile-update-delete'
    ),

    # Task
    path(
        'task/',
        TaskAPIView.as_view(),
        name='task-create'
    ),
    path(
        'task/<int:pk>/',
        TaskAPIView.as_view(),
        name='task-update-delete'
    ),

    # Instructor
    path(
        'instructor/',
        InstructorAPIView.as_view(),
        name='instructor-create'
    ),
    path(
        'instructor/<int:pk>/',
        InstructorAPIView.as_view(),
        name='instructor-update-delete'
    ),

    # Schedule
    path(
        'schedule/',
        ScheduleAPIView.as_view(),
        name='schedule-create'
    ),
    path(
        'schedule/<int:pk>/',
        ScheduleAPIView.as_view(),
        name='schedule-update-delete'
    ),




]