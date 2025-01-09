import base64
import requests

from .models import FileUpload
from utils.s3_utils import upload_file_to_s3

from django.shortcuts import get_object_or_404
from drf_yasg.inspectors import SwaggerAutoSchema
from botocore.exceptions import NoCredentialsError
from .serializers import FileUploadSerializer, FileUrlSerializer

from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser


class FileUploadSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['File Hub']


class FileUploadCreateView(generics.CreateAPIView):
    serializer_class = FileUploadSerializer
    parser_classes = (MultiPartParser, FormParser)
    swagger_schema = FileUploadSwaggerAutoSchema

    def create(self, request, *args, **kwargs):
        if 'file' not in request.FILES:
            return Response({'error': 'No file was submitted.'}, status=status.HTTP_400_BAD_REQUEST)

        file_data = request.FILES['file']

        try:
            upload_file_to_s3(file_data)
            validated_data = self.get_validated_data(request, file_data)
            self.save_serializer(validated_data)

            return Response({
                'status': 'success',
                'message': 'File successfully uploaded to S3.'
            }, status=status.HTTP_201_CREATED)
        except NoCredentialsError:
            return Response({'status': 'error', 'detail': 'AWS credentials not available.'},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'detail': str(e),
            }, status=status.HTTP_400_BAD_REQUEST)

    def get_validated_data(self, request, file_data):
        return {
            'date': request.data['date'],
            'title': request.data['title'],
            'description': request.data['description'],
            'file': file_data,
        }

    def save_serializer(self, validated_data):
        serializer = self.get_serializer(data=validated_data)
        serializer.is_valid(raise_exception=True)
        serializer.save()


class FileDeleteView(generics.DestroyAPIView):
    queryset = FileUpload.objects.all()
    swagger_schema = FileUploadSwaggerAutoSchema

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object_or_none()

        if not instance:
            return Response({'status': 'error', 'detail': 'File not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Delete the database record
            instance.delete()
            return Response({'status': 'success', 'message': 'File successfully deleted.'},
                            status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'status': 'error', 'detail': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)

    def get_object_or_none(self):
        return get_object_or_404(self.queryset, pk=self.kwargs.get('pk', None))


class FileListView(generics.ListAPIView):
    queryset = FileUpload.objects.all()
    serializer_class = FileUploadSerializer
    swagger_schema = FileUploadSwaggerAutoSchema


class FileRetrieveView(generics.RetrieveAPIView):
    queryset = FileUpload.objects.all()
    serializer_class = FileUploadSerializer
    swagger_schema = FileUploadSwaggerAutoSchema


class FileUpdateView(generics.UpdateAPIView):
    queryset = FileUpload.objects.all()
    serializer_class = FileUploadSerializer
    swagger_schema = FileUploadSwaggerAutoSchema


class ConvertFileToBase64View(generics.CreateAPIView):
    serializer_class = FileUrlSerializer
    parser_classes = (MultiPartParser, FormParser)
    swagger_schema = FileUploadSwaggerAutoSchema

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_url = serializer.validated_data['file_url']

        try:
            response = requests.get(file_url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return Response({'status': 'error', 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        file_content = response.content
        file_extension = file_url.split('.')[-1]

        # Convert file content to base64
        base64_content = base64.b64encode(file_content).decode('utf-8')

        # Return base64 content in the API response
        return Response({'base64_content': base64_content, 'file_extension': file_extension}, status=status.HTTP_200_OK)
