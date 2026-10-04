from django.contrib.auth import login, logout
from django.middleware.csrf import get_token
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from projects.models import UserProfile, Department
from projects.task_permissions import role_capabilities
from projects.serializers import UserProfileSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import LoginSerializer

class LoginAPIView(APIView):
    def get(self, request, *args, **kwargs):
        return Response({'csrf_token': get_token(request)})

    def post(self, request, *args, **kwargs):
        # Pass request context so authenticate() can use it if needed
        serializer = LoginSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            return Response({
                "message": "Login successful",
                "user_id": user.id,
                "username": user.username,
                "capabilities": role_capabilities(user)
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ForgotPasswordAPIView(APIView):
    def post(self, request, *args, **kwargs):
        return Response(
            {"message": "Please contact IT support team"},
            status=status.HTTP_200_OK
        )


class MyProfileAPIView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return Response({
            'profile': UserProfileSerializer(profile).data,
            'departments': list(Department.objects.values('id', 'name')),
            'csrf_token': get_token(request),
            'capabilities': role_capabilities(request.user),
        })

    def patch(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'profile': serializer.data})


class LogoutAPIView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'message': 'Logged out successfully'})
