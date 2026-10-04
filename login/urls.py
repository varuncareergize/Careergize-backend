from django.urls import path
from .views import LoginAPIView, ForgotPasswordAPIView, MyProfileAPIView, LogoutAPIView

urlpatterns = [
    path('profile/', MyProfileAPIView.as_view(), name='my-profile'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path('login/', LoginAPIView.as_view(), name='api_login'),
    path('forgot-password/', ForgotPasswordAPIView.as_view(), name='forgot_password'),
]
