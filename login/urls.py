from django.urls import path
from .views import LoginAPIView, ForgotPasswordAPIView

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='api_login'),
    path('forgot-password/', ForgotPasswordAPIView.as_view(), name='forgot_password'),
]