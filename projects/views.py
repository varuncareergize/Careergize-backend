from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .task_permissions import is_hr_admin, can_manage_project, is_manager
from django.db import transaction
from .models import Client, Team, Project
from .serializers import ClientSerializer, TeamSerializer, ProjectSerializer, UserSerializer


class ClientListCreateAPIView(APIView):
    """
    List all clients or create a new client.
    """

    def get(self, request):
        clients = Client.objects.select_related('assigned_to').all()
        serializer = ClientSerializer(clients, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ClientSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClientDetailAPIView(APIView):
    """
    Retrieve, update, or delete a specific client.
    """

    def get_object(self, pk):
        try:
            return Client.objects.get(pk=pk)
        except Client.DoesNotExist:
            return None

    def get(self, request, pk):
        client = self.get_object(pk)
        if not client:
            return Response(
                {"error": "Client not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ClientSerializer(client)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        client = self.get_object(pk)
        if not client:
            return Response(
                {"error": "Client not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ClientSerializer(client, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        client = self.get_object(pk)
        if not client:
            return Response(
                {"error": "Client not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ClientSerializer(client, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        client = self.get_object(pk)
        if not client:
            return Response(
                {"error": "Client not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        client.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TeamListCreateAPIView(APIView):
    """
    List all teams or create a new team.
    """

    def get(self, request):
        teams = Team.objects.all()
        serializer = TeamSerializer(teams, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = TeamSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TeamDetailAPIView(APIView):
    """
    Retrieve, update, or delete a specific team.
    """

    def get_object(self, pk):
        try:
            return Team.objects.get(pk=pk)
        except Team.DoesNotExist:
            return None

    def get(self, request, pk):
        team = self.get_object(pk)
        if not team:
            return Response(
                {"error": "Team not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = TeamSerializer(team)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        team = self.get_object(pk)
        if not team:
            return Response(
                {"error": "Team not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = TeamSerializer(team, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        team = self.get_object(pk)
        if not team:
            return Response(
                {"error": "Team not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = TeamSerializer(team, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        team = self.get_object(pk)
        if not team:
            return Response(
                {"error": "Team not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        team.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserListAPIView(APIView):
    """
    List all registered users.
    """

    def get(self, request):
        users = get_user_model().objects.select_related(
            'profile__department',
        ).order_by('username')
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProjectListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    """
    List all projects or create a new project.
    """

    def get(self, request):
        projects = Project.objects.filter(is_active=True)
        if not is_hr_admin(request.user):
            projects = projects.filter(Q(project_manager=request.user) | Q(assigned_users=request.user) | Q(tasks__assigned_to=request.user)).distinct()
        serializer = ProjectSerializer(projects, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if not (is_hr_admin(request.user) or is_manager(request.user)):
            raise PermissionDenied('Only HR/admin or managers can create projects.')
        serializer = ProjectSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(**({} if is_hr_admin(request.user) else {'project_manager': request.user}))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProjectDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    """
    Retrieve, update, or delete a specific project.
    """

    def get_object(self, pk):
        try:
            queryset = Project.objects.all()
            if not is_hr_admin(self.request.user):
                queryset = queryset.filter(Q(project_manager=self.request.user) | Q(assigned_users=self.request.user) | Q(tasks__assigned_to=self.request.user)).distinct()
            project = queryset.get(pk=pk)
            if self.request.method != 'GET' and not can_manage_project(self.request.user, project):
                raise PermissionDenied('Only HR/admin or the project manager can edit this project.')
            return project
        except Project.DoesNotExist:
            return None

    def get(self, request, pk):
        project = self.get_object(pk)
        if not project:
            return Response(
                {"error": "Project not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ProjectSerializer(project, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        project = self.get_object(pk)
        if not project:
            return Response(
                {"error": "Project not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ProjectSerializer(project, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        project = self.get_object(pk)
        if not project:
            return Response(
                {"error": "Project not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ProjectSerializer(project, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def delete(self, request, pk):
        project = self.get_object(pk)
        if not project:
            return Response(
                {"error": "Project not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        project.is_active = False
        project.save(update_fields=['is_active', 'updated_at'])
        project.tasks.update(is_active=False)
        return Response(status=status.HTTP_204_NO_CONTENT)
