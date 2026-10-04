from django.urls import path
from .task_views import TaskListView, TaskDetailView, TaskDailyUpdateView, TaskCommentView, TaskAttachmentView, TaskAttachmentDownloadView, TaskOptionsView

urlpatterns = [
    path('tasks/', TaskListView.as_view(), name='task-list'),
    path('task-options/', TaskOptionsView.as_view(), name='task-options'),
    path('tasks/<int:pk>/', TaskDetailView.as_view(), name='task-detail'),
    path('tasks/<int:pk>/updates/', TaskDailyUpdateView.as_view(), name='task-updates'),
    path('tasks/<int:pk>/comments/', TaskCommentView.as_view(), name='task-comments'),
    path('tasks/<int:pk>/attachments/', TaskAttachmentView.as_view(), name='task-attachments'),
    path('tasks/<int:pk>/attachments/<int:attachment_pk>/download/', TaskAttachmentDownloadView.as_view(), name='task-attachment-download'),
]
