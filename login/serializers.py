from django.contrib.auth import authenticate
from rest_framework import serializers

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(
        required=True, write_only=True, style={'input_type': 'password'}
    )

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(request=self.context.get('request'), username=username, password=password)

            if not user:
                raise serializers.ValidationError("Invalid username or password.")
            
            if not user.is_active:
                raise serializers.ValidationError("This user account is disabled.")
        else:
            raise serializers.ValidationError("Must include 'username' and 'password'.")

        # Pass the authenticated user forward to the view
        attrs['user'] = user
        return attrs