from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Client, Team, Project


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = "__all__"


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = "__all__"


class ProjectSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)
    amount_left = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    assigned_users = UserSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = "__all__"
