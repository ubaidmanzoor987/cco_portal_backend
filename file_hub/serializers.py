# serializers.py
from rest_framework import serializers
from .models import FileUpload
from decouple import config


class FileUploadSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)

    class Meta:
        model = FileUpload
        fields = ['id', 'date', 'title', 'description', 'file', 's3_file_link']
        read_only_fields = ['s3_file_link']

    def create(self, validated_data):
        bucket_name = config('S3_BUCKET_NAME')
        # Extract 'file' from validated_data
        file_data = validated_data.pop('file', None)

        # Create the model instance without 'file' field
        instance = super().create(validated_data)

        # If 'file' is present, set 's3_file_link' based on the S3 file path
        if file_data:
            s3_file_path = f'https://{bucket_name}.s3.amazonaws.com/{file_data.name}'
            instance.s3_file_link = s3_file_path
            instance.save()

        return instance


class FileUrlSerializer(serializers.Serializer):
    file_url = serializers.CharField()
