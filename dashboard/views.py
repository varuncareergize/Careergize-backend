# dashboard/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User

from .models import (
    StudentProfile,
    Task,
    Instructor,
    Schedule
)

from .serializers import (
    StudentProfileSerializer,
    TaskSerializer,
    InstructorSerializer,
    ScheduleSerializer,
    DashboardSerializer
)

class StudentDashboardAPIView(APIView):

    def get(self, request, *args, **kwargs):

        user = User.objects.filter(id=2).first()

        if not user:
            return Response(
                {"error": "Student account not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DashboardSerializer(user)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

class StudentProfileAPIView(APIView):

    def get(self, request, pk=None):

        # Get single profile
        if pk:
            try:
                profile = StudentProfile.objects.get(id=pk)
                serializer = StudentProfileSerializer(profile)
                return Response(serializer.data)

            except StudentProfile.DoesNotExist:
                return Response(
                    {"error": "Profile not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Get all profiles
        profiles = StudentProfile.objects.all()
        serializer = StudentProfileSerializer(profiles, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = StudentProfileSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            profile = StudentProfile.objects.get(id=pk)
        except StudentProfile.DoesNotExist:
            return Response(
                {"error": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = StudentProfileSerializer(
            profile,
            data=request.data
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            profile = StudentProfile.objects.get(id=pk)
        except StudentProfile.DoesNotExist:
            return Response(
                {"error": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        profile.delete()
        return Response(
            {"message": "Profile deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )
    

class TaskAPIView(APIView):

    def get(self, request, pk=None):
        if pk:
            try:
                task = Task.objects.get(id=pk)
                serializer = TaskSerializer(task)
                return Response(serializer.data)
            except Task.DoesNotExist:
                return Response({"error": "Task not found"}, status=404)

        serializer = TaskSerializer(Task.objects.all(), many=True)
        return Response(serializer.data)


    def post(self, request):
        serializer = TaskSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            task = Task.objects.get(id=pk)
        except Task.DoesNotExist:
            return Response(
                {"error": "Task not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TaskSerializer(task, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            task = Task.objects.get(id=pk)
        except Task.DoesNotExist:
            return Response(
                {"error": "Task not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        task.delete()

        return Response(
            {"message": "Task deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )

class InstructorAPIView(APIView):

    def post(self, request):
        serializer = InstructorSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            instructor = Instructor.objects.get(id=pk)
        except Instructor.DoesNotExist:
            return Response(
                {"error": "Instructor not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = InstructorSerializer(
            instructor,
            data=request.data
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            instructor = Instructor.objects.get(id=pk)
        except Instructor.DoesNotExist:
            return Response(
                {"error": "Instructor not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        instructor.delete()

        return Response(
            {"message": "Instructor deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )

class ScheduleAPIView(APIView):

    def get(self, request, pk=None):
        if pk:
            try:
                schedule = Schedule.objects.get(id=pk)
                serializer = ScheduleSerializer(schedule)
                return Response(serializer.data)
            except Schedule.DoesNotExist:
                return Response({"error": "Schedule not found"}, status=404)

        serializer = ScheduleSerializer(
            Schedule.objects.all(),
            many=True
        )
        return Response(serializer.data)

    def post(self, request):
        serializer = ScheduleSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            schedule = Schedule.objects.get(id=pk)
        except Schedule.DoesNotExist:
            return Response(
                {"error": "Schedule not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ScheduleSerializer(
            schedule,
            data=request.data
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            schedule = Schedule.objects.get(id=pk)  
        except Schedule.DoesNotExist:
            return Response(
                {"error": "Schedule not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        schedule.delete()

        return Response(
            {"message": "Schedule deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )