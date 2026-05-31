from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Attendance
from dashboard.models import Schedule
from .serializer import AttendanceSerializer

class MarkAttendanceAPIView(APIView):

    def post(self, request):

        username = request.data.get("username")

        if username:
            try:
                target_user = User.objects.get(username__iexact=username)
            except User.DoesNotExist:
                return Response(
                    {"success": False, "message": "User not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        elif request.user.is_authenticated:
            target_user = request.user
        else:
            return Response(
                {"success": False, "message": "Username is required for unauthenticated access"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Automatically find the schedule for the student for the current date
        today = timezone.now().date()
        schedule = Schedule.objects.filter(
            student=target_user,
            start_time__date=today
        ).order_by('start_time').first()

        if not schedule:
            return Response(
                {"success": False, "message": "No schedule found for this user today"},
                status=status.HTTP_404_NOT_FOUND
            )

        attendance, created = Attendance.objects.get_or_create(
            student=target_user,
            schedule=schedule
        )

        if not created:
            return Response(
                {
                    "success": False,
                    "message": "Attendance already marked"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        attendance.status = "present"
        attendance.check_in_time = timezone.now()
        attendance.save()

        return Response(
            {
                "success": True,
                "message": "Attendance marked successfully"
            }
        )
    

class AttendanceListAPIView(APIView):

    def get(self, request):
        username = request.query_params.get("username")

        if username:
            attendances = Attendance.objects.filter(student__username__iexact=username)
        elif request.user.is_authenticated:
            attendances = Attendance.objects.filter(student=request.user)
        else:
            return Response(
                {"success": False, "message": "Username parameter is required for unauthenticated access"},
                status=status.HTTP_400_BAD_REQUEST
            )

        attendances = attendances.order_by('-created_at')

        serializer = AttendanceSerializer(
            attendances,
            many=True
        )

        return Response(
            {
                "success": True,
                "data": serializer.data
            }
        )





class AttendanceStatusAPIView(APIView):

    def get(self, request):
        username = request.query_params.get("username")
        today = timezone.now().date()

        filter_params = {"created_at__date": today}
        
        if username:
            filter_params["student__username__iexact"] = username
        elif request.user.is_authenticated:
            filter_params["student"] = request.user
        else:
            return Response(
                {"success": False, "message": "Username parameter is required for unauthenticated access"},
                status=status.HTTP_400_BAD_REQUEST
            )

        attendance = Attendance.objects.filter(**filter_params).exists()

        return Response({
            "success": True,
            "marked": attendance
        })