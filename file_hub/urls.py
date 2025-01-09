from django.urls import path
from .views import FileUploadCreateView, FileDeleteView, FileListView, FileRetrieveView, FileUpdateView, \
    ConvertFileToBase64View

urlpatterns = [
    path('file/upload/', FileUploadCreateView.as_view(), name='file-upload-create'),
    path('file/<int:pk>/delete/', FileDeleteView.as_view(), name='file-delete'),
    path('file/', FileListView.as_view(), name='file-list'),
    path('file/<int:pk>/', FileRetrieveView.as_view(), name='file-detail'),
    path('file/<int:pk>/update/', FileUpdateView.as_view(), name='file-update'),
    path('file/convert/', ConvertFileToBase64View.as_view(), name='convert_file_to_base64'),
]
