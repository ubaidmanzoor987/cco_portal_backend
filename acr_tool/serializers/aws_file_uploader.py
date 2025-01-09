from datetime import datetime
from rest_framework import serializers
from acr_tool.models import AWSResourceFile
from utils.s3_utils import upload_file_to_s3_folder


class AWSResourceFileSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)

    class Meta:
        model = AWSResourceFile
        fields = ['acr_tab', 'resource_file_s3_link', 'file', 'created_at', 'updated_at', 'created_by']
        read_only_fields = ['resource_file_s3_link', 'created_at', 'updated_at', 'created_by']

    def create(self, validated_data):
        file = validated_data.pop('file', None)
        acr_tab = validated_data['acr_tab']
        user = self.context['request'].user

        if file:
            root_folder_name = "acr_reports"
            current_year = datetime.utcnow().year
            folder_name = f"{root_folder_name}/{current_year}"

            resource_s3_file_link = upload_file_to_s3_folder(
                file.read(),
                file.name,
                file.content_type,
                folder_name
            )

            return AWSResourceFile.objects.create(
                acr_tab=acr_tab,
                resource_file_s3_link=[resource_s3_file_link],
                created_by=user
            )

    def update(self, instance, validated_data):
        file = validated_data.pop('file', None)

        if file:
            root_folder_name = "acr_reports"
            current_year = datetime.utcnow().year
            folder_name = f"{root_folder_name}/{current_year}"

            resource_s3_file_link = upload_file_to_s3_folder(
                file.read(),
                file.name,
                file.content_type,
                folder_name
            )
            instance.resource_file_s3_link = [resource_s3_file_link]

        instance.save()
        return instance
