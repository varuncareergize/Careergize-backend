from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Client, Team, Project, UserProfile
from django.db import transaction


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name', max_length=150, allow_blank=True, required=False)
    last_name = serializers.CharField(source='user.last_name', max_length=150, allow_blank=True, required=False)
    email = serializers.EmailField(source='user.email', max_length=254, allow_blank=True, required=False)
    department_name = serializers.CharField(source='department.name', read_only=True, default=None)

    class Meta:
        model = UserProfile
        fields = [
            'username', 'first_name', 'last_name', 'email', 'phone_number',
            'address', 'city', 'state', 'postal_code', 'country', 'department',
            'department_name', 'date_of_birth', 'bank_name',
            'bank_account_holder_name', 'bank_account_number', 'bank_ifsc_code',
            'bank_branch', 'created_at', 'updated_at',
        ]
        read_only_fields = ['department', 'created_at', 'updated_at']

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        if user_data:
            for field, value in user_data.items():
                setattr(instance.user, field, value)
            instance.user.save(update_fields=list(user_data))
        return super().update(instance, validated_data)


class UserSerializer(serializers.ModelSerializer):
    department = serializers.IntegerField(
        source='profile.department_id', read_only=True, default=None,
    )
    department_name = serializers.CharField(
        source='profile.department.name', read_only=True, default=None,
    )

    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'department', 'department_name']


class ClientSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True, default=None)

    class Meta:
        model = Client
        fields = "__all__"


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = "__all__"


class ProjectSerializer(serializers.ModelSerializer):
    can_manage = serializers.SerializerMethodField()

    def get_can_manage(self, project):
        from .task_permissions import can_manage_project
        request = self.context.get('request')
        return bool(request and can_manage_project(request.user, project))

    client_name = serializers.CharField(source="client.name", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)
    amount_left = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    assigned_users = serializers.PrimaryKeyRelatedField(
        many=True, queryset=get_user_model().objects.all(), required=False,
    )
    assigned_user_details = UserSerializer(source='assigned_users', many=True, read_only=True)
    project_manager_name = serializers.CharField(source='project_manager.username', read_only=True, default=None)

    class Meta:
        model = Project
        fields = "__all__"

    def validate(self, attrs):
        start = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        expected = attrs.get('expected_delivery_date', getattr(self.instance, 'expected_delivery_date', None))
        actual = attrs.get('actual_delivery_date', getattr(self.instance, 'actual_delivery_date', None))
        errors = {}
        if start and expected and expected < start:
            errors['expected_delivery_date'] = 'Expected delivery must be on or after the start date.'
        if start and actual and actual < start:
            errors['actual_delivery_date'] = 'Actual delivery must be on or after the start date.'
        if errors:
            raise serializers.ValidationError(errors)
        return attrs
