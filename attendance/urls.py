from django.urls import path
from .views import MarkAttendanceAPIView, AttendanceListAPIView, AttendanceStatusAPIView

urlpatterns = [

    path(
        'attendance/mark/',
        MarkAttendanceAPIView.as_view()
    ),

    path(
        'attendance/list/',
        AttendanceListAPIView.as_view()
    ),

    path(
        'attendance/status/',
        AttendanceStatusAPIView.as_view()
    ),

]