from django.urls import path
from .overview_views import OverviewView
from .views import (
    ClientListCreateAPIView,
    ClientDetailAPIView,
    TeamListCreateAPIView,
    TeamDetailAPIView,
    UserListAPIView,
    ProjectListCreateAPIView,
    ProjectDetailAPIView,
)

urlpatterns = [
    path('overview/', OverviewView.as_view(), name='overview'),
    # Client URLs
    path('clients/', ClientListCreateAPIView.as_view(), name='client-list-create'),
    path('clients/<int:pk>/', ClientDetailAPIView.as_view(), name='client-detail'),
    
    # Team URLs
    path('teams/', TeamListCreateAPIView.as_view(), name='team-list-create'),
    path('teams/<int:pk>/', TeamDetailAPIView.as_view(), name='team-detail'),
    
    # User URLs
    path('users/', UserListAPIView.as_view(), name='user-list'),

    # Project URLs
    path('projects/', ProjectListCreateAPIView.as_view(), name='project-list-create'),
    path('projects/<int:pk>/', ProjectDetailAPIView.as_view(), name='project-detail'),
]
