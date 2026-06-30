from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Client, Team, Project


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
    assigned_users = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=get_user_model().objects.all(),
        required=False,
    )

    class Meta:
        model = Project
        fields = "__all__"
