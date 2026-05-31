from django.contrib.auth.models import User

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import (
    StudentProfile,
    Task,
    Instructor,
    Schedule
)

from .serializers import (
    DashboardSerializer,
    StudentProfileSerializer,
    TaskSerializer,
    InstructorSerializer,
    ScheduleSerializer
)


class StudentDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = DashboardSerializer(user)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class TaskAPIView(APIView):

    def get(self, request):

        tasks = Task.objects.all()

        serializer = TaskSerializer(
            tasks,
            many=True
        )

        return Response(serializer.data)

    def post(self, request):

        serializer = TaskSerializer(
            data=request.data
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=201
            )

        return Response(
            serializer.errors,
            status=400
        )


class ScheduleAPIView(APIView):

    def get(self, request):

        schedules = Schedule.objects.all()

        serializer = ScheduleSerializer(
            schedules,
            many=True
        )

        return Response(serializer.data)

    def post(self, request):

        serializer = ScheduleSerializer(
            data=request.data
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=201
            )

        return Response(
            serializer.errors,
            status=400
        )


class InstructorAPIView(APIView):

    def get(self, request):

        instructors = Instructor.objects.all()

        serializer = InstructorSerializer(
            instructors,
            many=True
        )

        return Response(serializer.data)

    def post(self, request):

        serializer = InstructorSerializer(
            data=request.data
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=201
            )

        return Response(
            serializer.errors,
            status=400
        )