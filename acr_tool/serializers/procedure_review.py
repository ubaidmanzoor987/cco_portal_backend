from task.models import Task
from datetime import datetime
from rest_framework import serializers

from acr_tool.models import *
from utils.s3_utils import upload_file_to_s3_folder


class ProcedureReviewInstructionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcedureReviewInstructions
        fields = ['id', 'instructions', 'overview', 'created_by', 'created_at']
        read_only_fields = ['created_by', 'created_at']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        instance.instructions = validated_data.get('instructions', instance.instructions)
        instance.overview = validated_data.get('overview', instance.overview)  # Updated field name
        instance.save()
        return instance


class TasksSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'task_title', 'due_date']


class ProcedureReviewSerializer(serializers.ModelSerializer):
    task = TasksSerializer(many=True, read_only=True)  # Serialize the task field with TaskSerializer
    task_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    compliance_calender_report_file = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = ProcedureReview
        fields = ['id', 'task', 'task_ids', 'organization', 'compliance_calender_report_link', 'created_by',
                  'created_at', 'compliance_calender_report_file']
        read_only_fields = ['id', 'task', 'organization', 'compliance_calender_report_link', 'created_at', 'created_by']

    def validate_task_ids(self, value):
        if value is None or (isinstance(value, list) and len(value) == 0):
            return []  # Return an empty list if task_ids is None or an empty list
        return self._validate_list_of_integers(value, 'task_ids')

    def _validate_list_of_integers(self, value, field_name):
        if isinstance(value, str):
            try:
                value = [int(id) for id in value.split(',')]
            except ValueError:
                raise serializers.ValidationError(f"Invalid format for {field_name}. Must be a list of integers.")
        if not all(isinstance(id, int) for id in value):
            raise serializers.ValidationError(f"Invalid format for {field_name}. All elements must be integers.")
        return value

    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        task_ids = validated_data.pop('task_ids', [])
        report_file = validated_data.pop('compliance_calender_report_file', None)

        # Assign organization
        if user.is_superuser:
            validated_data['organization'] = None
        else:
            validated_data['organization'] = user.organization

        validated_data['created_by'] = user
        procedure_review = super().create(validated_data)

        if report_file:
            # Handle file upload to S3
            file_content = report_file.read()
            file_name = report_file.name
            content_type = report_file.content_type
            folder_name = f'procedure_reviews/{procedure_review.id}'
            resource_s3_file_link = upload_file_to_s3_folder(file_content, file_name, content_type, folder_name)
            procedure_review.compliance_calender_report_link = resource_s3_file_link
            procedure_review.save()

        # Assign the tasks to the ProcedureReview instance
        # Only link tasks that exist and have 'Completed' status
        valid_tasks = Task.objects.filter(id__in=task_ids, task_status='Completed')
        procedure_review.task.set(valid_tasks)

        # Ignore tasks that do not exist or do not have 'Completed' status
        return procedure_review

    def update(self, instance, validated_data):
        task_ids = validated_data.pop('task_ids', None)
        report_file = validated_data.pop('compliance_calender_report_file', None)

        if task_ids is not None:
            # Fetch tasks that exist and have 'Completed' status
            valid_tasks = Task.objects.filter(id__in=task_ids, task_status='Completed')

            # Update the task relationships
            instance.task.set(valid_tasks)
        else:
            # If task_ids is None, remove all linked tasks
            instance.task.clear()

        if report_file:
            # Handle file upload to S3
            file_content = report_file.read()
            file_name = report_file.name
            content_type = report_file.content_type
            folder_name = f'procedure_reviews/{instance.id}'
            resource_s3_file_link = upload_file_to_s3_folder(file_content, file_name, content_type, folder_name)
            instance.compliance_calender_report_link = resource_s3_file_link

        # Update any other fields passed in validated_data
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
