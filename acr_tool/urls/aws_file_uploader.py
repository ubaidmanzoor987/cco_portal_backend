from django.urls import path
from acr_tool.views import AWSResourceFileViewSet

aws_resource_file_patterns = [
    path('', AWSResourceFileViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='aws_resource_file_list'),
    path('<int:pk>/', AWSResourceFileViewSet.as_view({'get': 'retrieve'}),
         name='aws_resource_file_detail'),
    path('<int:pk>/delete/', AWSResourceFileViewSet.as_view({'delete': 'destroy'}),
         name='aws_resource_file_delete'),
    path('current_year/', AWSResourceFileViewSet.as_view({'get': 'current_year_records'}),
         name='current_year_records'),
]
