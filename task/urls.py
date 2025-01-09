from django.urls import path
from .views import TaskViewSet, TaskHistoryViewSet, ArchiveTasksView

urlpatterns = [
    path('task/create/', TaskViewSet.as_view({'post': 'create'}), name='task_create'),
    path('task/', TaskViewSet.as_view({'get': 'list'}), name='task_list'),
    path('task/<int:pk>/', TaskViewSet.as_view({'get': 'retrieve'}), name='task_detail'),
    path('task/<int:pk>/update/', TaskViewSet.as_view({'put': 'update', 'patch': 'partial_update'}),
         name='task_update'),
    path('task/<int:pk>/delete/', TaskViewSet.as_view({'delete': 'destroy'}), name='task_delete'),
    path('task/history/', TaskHistoryViewSet.as_view({'get': 'list'}), name='task_history_list'),
    path('task/history/<int:pk>/', TaskHistoryViewSet.as_view({'get': 'retrieve'}), name='task_history_detail'),
    path('task/org-tasks/', TaskViewSet.as_view({'get': 'get_org_tasks'}), name='task_org_tasks'),
    path('task/archive/', ArchiveTasksView.as_view(), name='task_archive'),
]
