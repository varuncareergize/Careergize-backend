from django.urls import path
from .views import AttendanceOptionsView, AttendanceTodayView, CheckInView, CheckOutView, AttendanceHistoryView, HRAttendanceView, AttendanceCorrectionView, AttendanceAuditView, LeaveListView, LeaveReviewView, LeaveCancelView

urlpatterns = [
    path('attendance/options/', AttendanceOptionsView.as_view()),
    path('attendance/today/', AttendanceTodayView.as_view()),
    path('attendance/check-in/', CheckInView.as_view()),
    path('attendance/check-out/', CheckOutView.as_view()),
    path('attendance/history/', AttendanceHistoryView.as_view()),
    path('attendance/hr/', HRAttendanceView.as_view()),
    path('attendance/hr/correct/', AttendanceCorrectionView.as_view()),
    path('attendance/<int:pk>/audit/', AttendanceAuditView.as_view()),
    path('leaves/', LeaveListView.as_view()),
    path('leaves/<int:pk>/review/', LeaveReviewView.as_view()),
    path('leaves/<int:pk>/cancel/', LeaveCancelView.as_view()),
]
