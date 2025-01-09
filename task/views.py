import json
import uuid
from django.utils import timezone
from django.db import transaction
from datetime import date, datetime
from botocore.exceptions import ClientError
from django.utils.dateparse import parse_datetime

from django.db.models import Q
from django.db.models import Prefetch
from rest_framework.views import APIView
from rest_framework import viewsets, status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from decouple import config
from .models import *
from .serializers import *
from utils.s3_utils import *
from django.utils.timezone import now
from accounts.models import CustomUser
from organization.models import Organization
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from drf_yasg.inspectors import SwaggerAutoSchema


class TaskSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['Tasks']


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    swagger_schema = TaskSwaggerAutoSchema
    bucket_name = config('S3_BUCKET_NAME')
    s3 = initialize_s3_client()

    def create(self, request, *args, **kwargs):
        user = request.user
        if not (user.is_superuser or user.role == 'CCO'):
            return Response(
                {"status": "error", "message": "Permission denied. Only superusers or CCO users can create tasks."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Determine user role
        user_role = 'admin' if user.is_superuser else 'CCO'

        # Initialize cleaned data and file fields
        cleaned_data = {}
        file_fields = {}

        # Process request data
        for key, value in request.data.items():
            if hasattr(value, 'read'):  # Check if it's a file-like object
                file_fields[key] = value  # Handle file-like objects separately
            elif key in ["changes_data", "resource_file_s3_links", "frequency_due_date", "user_list"]:
                # Parse JSON fields
                try:
                    cleaned_data[key] = json.loads(value)
                except json.JSONDecodeError:
                    return Response(
                        {key: [f"{key} must be a valid JSON string."]},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Add non-file fields to cleaned data
                cleaned_data[key] = value

        # Handle organization_ids and organization_user_ids as lists
        organization_ids = cleaned_data.get('organization_ids', "").split(',')
        cleaned_data['organization_ids'] = [org_id.strip() for org_id in organization_ids if org_id.strip().isdigit()]

        organization_user_ids = cleaned_data.get('organization_user_ids', "").split(',')
        if user_role == 'CCO' and not organization_user_ids:
            return Response(
                {"status": "error", "message": "organization_user_ids field is required for CCO users."},
                status=status.HTTP_400_BAD_REQUEST
            )
        cleaned_data['organization_user_ids'] = [user_id.strip() for user_id in organization_user_ids if
                                                 user_id.strip().isdigit()]

        # Add file fields to cleaned_data for serializer processing
        cleaned_data.update(file_fields)

        # Serialize data
        serializer = self.get_serializer(data=cleaned_data)
        serializer.is_valid(raise_exception=True)
        all_task_data = serializer.save()

        # Additional processing for tasks
        changes_data = serializer.validated_data.get('changes_data', [])
        resource_file_s3_links = serializer.validated_data.get('resource_file_s3_links', [])
        # Flag to track the first iteration
        is_first_iteration = True

        for task_data in all_task_data:
            # Calculate task status based on due_date
            due_date = task_data.due_date
            task_status = "Upcoming"
            if due_date:
                due_date = parse_datetime(due_date)
                current_date = datetime.utcnow()

                if due_date.date() == current_date.date():
                    task_status = "Pending"
                elif due_date.date() < current_date.date():
                    task_status = "Overdue"

            # Only create folders and upload files in the first iteration
            if is_first_iteration:
                self._create_folders(["Organizations", "Resource Files"])
                additional_files = [request.FILES.get(f"file_{i}") for i in range(1, 6) if f"file_{i}" in request.FILES]
                resource_file_s3_links = self._upload_files(organization_ids, additional_files, task_data)
                is_first_iteration = False

            if changes_data:
                current_utc_time = datetime.utcnow().strftime('%d-%m-%Y %H:%M:%S %p')
                changes_data[0]["date_time"] = current_utc_time

            task_history = TaskHistory.objects.create(changes_data=changes_data)

            task_data.task_status = task_status
            task_data.resource_file_s3_links = resource_file_s3_links
            task_data.task_history = task_history
            task_data.save()

            for organization_id in organization_ids:
                self._create_organization_task(organization_id, task_data, user_role, organization_user_ids)

        return Response({"status": "success", 'message': 'Task created successfully.'}, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.is_superuser:
                # return Task.objects.all(), "admin"
                return Task.objects.filter(organizationtask__isnull=False).distinct(), "admin"
            elif hasattr(user, 'organization'):
                return Task.objects.filter(
                    id__in=OrganizationUserTask.objects.filter(organization_user=user.id).values_list('task_id',
                                                                                                      flat=True)
                ), "cco"
        return Task.objects.none(), "cco"

    def list(self, request, *args, **kwargs):
        queryset, user_role = self.get_queryset()
        if not queryset.exists():
            return Response(
                {"status": "error", "message": "No tasks found for the current logged in user."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        for item in data:
            item.update({
                'task_history': self.get_changes_data(item['task_history']),
                'task_status': self.get_task_status(item['id']),
                'user_role': request.user.role
            })

            if user_role == "admin":
                organization_task_qs = OrganizationTask.objects.filter(task=item['id'])
                organization_ids = [entry.organization_id for entry in organization_task_qs]
                # if not organization_ids:
                #     organization_ids = OrganizationUserTask.objects.filter(task=item['id']).first().organization_id
                item['organization_ids'] = ",".join(map(str, organization_ids))
            elif user_role == "cco":
                organization_user_task_qs = OrganizationUserTask.objects.filter(task=item['id'])
                organization_user_ids = [entry.organization_user_id for entry in organization_user_task_qs]
                organization_user_ids = ",".join(map(str, organization_user_ids))
                organization_id = [OrganizationUserTask.objects.filter(task=item['id']).first().organization_id]
                organization_id = ",".join(map(str, organization_id))
                item.update({
                    'organization_ids': organization_id,
                    'organization_user_ids': organization_user_ids,
                })

        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        user = self.request.user
        user_role = "admin" if user.is_superuser else "cco"
        task_id = kwargs['pk']

        if user_role == "cco":
            if (not OrganizationUserTask.objects.filter(organization_user=user.id, task_id=task_id).exists()
                    and not OrganizationTask.objects.filter(task_id=task_id, organization=user.organization).exists()):
                return Response(
                    {"status": "error", "message": f"Task with ID {task_id} not found for the current logged in user."},
                    status=status.HTTP_404_NOT_FOUND
                )

        try:
            task = get_object_or_404(Task, id=task_id)
        except:
            return Response(
                {"status": "error", "message": f"Task with ID {task_id} does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(task)
        data = serializer.data
        data.update({
            'task_history': self.get_changes_data(task.task_history.id),
            'task_status': self.get_task_status(task.id),
            'user_role': request.user.role
        })

        if user_role == "admin":
            organization_task_qs = OrganizationTask.objects.filter(task=task)
            organization_ids = [entry.organization_id for entry in organization_task_qs]
            # if not organization_ids:
            #     organization_ids = OrganizationUserTask.objects.filter(task=task).first().organization_id
            data['organization_ids'] = ",".join(map(str, organization_ids))
        elif user_role == "cco":
            organization_user_task_qs = OrganizationUserTask.objects.filter(task=task)
            organization_user_ids = [entry.organization_user_id for entry in organization_user_task_qs]
            organization_user_ids = ",".join(map(str, organization_user_ids))
            organization_id = [OrganizationUserTask.objects.filter(task=task).first().organization_id]
            organization_id = ",".join(map(str, organization_id))
            data.update({
                'organization_ids': organization_id,
                'organization_user_ids': organization_user_ids,
            })

        return Response(data)

    def get_task_status(self, task_id):
        task = get_object_or_404(Task, id=task_id)

        # Update overdue status for relevant tasks
        self._update_overdue_task_status(task)

        return task.task_status

    def _update_overdue_task_status(self, task):
        """
        Updates the task status to 'Overdue' if it is past the due date and not marked as 'Completed'.
        """
        # Get current date in UTC
        current_date = datetime.utcnow().date()

        # Check if the task's due date is in the past and its status is not 'Completed'
        if task.due_date and task.due_date < current_date and task.task_status not in [Task.STATUS_COMPLETED,
                                                                                       Task.STATUS_OVERDUE]:
            # Update the task's status to 'Overdue' if conditions are met
            task.task_status = Task.STATUS_OVERDUE
            task.save()

    def update(self, request, *args, **kwargs):
        user = request.user
        if not (user.is_superuser or user.role == 'CCO'):
            return Response(
                {"status": "error", "message": "Permission denied. Only superusers or CCO users can update tasks."},
                status=status.HTTP_403_FORBIDDEN
            )

        user_role = 'admin' if user.is_superuser else 'CCO'

        partial = kwargs.pop('partial', False)
        instance = get_object_or_404(Task, id=kwargs['pk'])

        # Initialize cleaned data
        cleaned_data = {}
        file_fields = {}

        # Process request data
        for key, value in request.data.items():
            if hasattr(value, 'read'):  # Check if it's a file-like object
                file_fields[key] = value  # Handle file-like objects separately
            elif key in ["changes_data", "resource_file_s3_links", "frequency_due_date", "user_list"]:
                # Parse JSON fields
                try:
                    cleaned_data[key] = json.loads(value)  # Convert JSON string to Python object
                except json.JSONDecodeError:
                    return Response(
                        {key: [f"{key} must be a valid JSON."]},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Add non-file fields to cleaned data
                cleaned_data[key] = value

        # Handle organization_ids and organization_user_ids as lists
        organization_ids = cleaned_data.get('organization_ids', "").split(',')
        cleaned_data['organization_ids'] = [org_id.strip() for org_id in organization_ids if org_id.strip().isdigit()]

        organization_user_ids = cleaned_data.get('organization_user_ids', "").split(',')
        cleaned_data['organization_user_ids'] = [user_id.strip() for user_id in organization_user_ids if
                                                 user_id.strip().isdigit()]

        # Add file fields to cleaned_data for serializer processing
        cleaned_data.update(file_fields)

        # Pass the cleaned data to the serializer
        serializer = self.get_serializer(instance, data=cleaned_data, partial=partial)
        serializer.is_valid(raise_exception=True)
        update_create_data = serializer.save(created_by=self.request.user)

        # Determine the structure of the update_create_data (updated instance and created tasks)
        updated_instance, created_tasks = self._extract_updated_and_created_tasks(update_create_data)

        # Serialize the updated instance
        updated_task_serializer = TaskSerializer(updated_instance, many=isinstance(updated_instance, list))

        # Handle tasks processing for created tasks
        self._process_created_tasks(
            created_tasks,
            serializer.validated_data.get('changes_data', []),
            serializer.validated_data.get('resource_file_s3_links', []),
            organization_ids,
            organization_user_ids,
            request,
            user_role
        )

        # Serialize created tasks
        created_tasks_serializer = TaskSerializer(created_tasks, many=True)

        # Prepare the response
        response_data = {
            "updated_task": updated_task_serializer.data,
            "created_tasks": created_tasks_serializer.data,
        }

        return Response(response_data)

    @swagger_auto_schema(
        operation_description="Delete a task and record the reason for deletion",
        request_body=DeletionReasonSerializer,
        responses={
            status.HTTP_204_NO_CONTENT: "Task successfully deleted",
            status.HTTP_403_FORBIDDEN: "Permission denied. You cannot delete this task.",
        }
    )
    def destroy(self, request, *args, **kwargs):
        """
        Main logic for handling the deletion of a task and linked tasks.
        """
        task = self.get_task(kwargs['pk'])
        user = request.user
        user_organization = user.organization

        if not self.can_delete_task(user, user_organization, task):
            return self.permission_denied_response()

        reason_for_deletion = request.data.get('reason_for_deletion', 'No reason provided')
        current_time = timezone.now()

        # Serialize task data (including the history) before deletion
        task_data = self.serialize_task_data(task)
        task_history_data = self.get_task_history_data(task, reason_for_deletion, current_time)

        # Fetch linked tasks
        linked_tasks = self.get_linked_tasks(task)

        # Process the linked tasks
        tasks_to_delete, tasks_to_update = self.split_tasks_by_status(linked_tasks)

        # Fetch deleted due dates and frequency periods
        deleted_due_dates = self.get_deleted_due_dates_and_periods(tasks_to_delete, task)

        # Delete tasks that are not completed
        self.delete_tasks(tasks_to_delete, reason_for_deletion, current_time, user_organization)

        # Update tasks that are completed
        self.update_completed_tasks(tasks_to_update, deleted_due_dates, task, reason_for_deletion)

        # Record the deletion of the main task if it's not completed
        if task.task_status != Task.STATUS_COMPLETED:
            self.create_deletion_history(task_data, task_history_data, user, user_organization, reason_for_deletion)
            task.delete()

        return Response(
            {"status": "success", "message": f"Task {task.id} and its linked tasks deleted successfully."},
            status=status.HTTP_200_OK
        )

    def _extract_updated_and_created_tasks(self, update_create_data):
        """
        Extracts the updated instance and created tasks from the saved data.
        """
        if isinstance(update_create_data, tuple):
            return update_create_data
        else:
            return update_create_data, []

    def _process_created_tasks(self, created_tasks, changes_data, resource_file_s3_links, organization_ids,
                               organization_user_ids, request, user_role):
        """
        Processes created tasks, updating their status, history, and handling file uploads.
        """
        is_first_iteration = True

        for task in created_tasks:  # Use model instances, not serialized data
            task_status = self._get_task_status(task.due_date)

            # Only create folders and upload files in the first iteration
            if is_first_iteration:
                self._create_folders(["Organizations", "Resource Files"])
                additional_files = [request.FILES.get(f"file_{i}") for i in range(1, 6) if f"file_{i}" in request.FILES]
                resource_file_s3_links = self._upload_files(organization_ids, additional_files, task)
                is_first_iteration = False

            # Add new logic for task history creation when task is created
            # -----------------------------------------------------------
            changes_data = [{'changes': [{'change': f'{request.user.username} created this task', 'file_upload': ''}]}]
            current_utc_time = datetime.utcnow().strftime('%d-%m-%Y %H:%M:%S %p')
            changes_data[0]["date_time"] = current_utc_time

            task_history = TaskHistory.objects.create(changes_data=changes_data)
            task.task_history = task_history
            task.save()
            # -----------------------------------------------------------

            # Process additional changes data if provided
            if changes_data:
                current_utc_time = datetime.utcnow().strftime('%d-%m-%Y %H:%M:%S %p')
                changes_data[0]["date_time"] = current_utc_time

            task_history = TaskHistory.objects.create(changes_data=changes_data)

            task.task_status = task_status
            task.resource_file_s3_links = resource_file_s3_links
            task.task_history = task_history
            task.save()

            for organization_id in organization_ids:
                self._create_organization_task(organization_id, task, user_role, organization_user_ids)

    def _get_task_status(self, due_date):
        """
        Determines the task status based on the due date.
        """
        task_status = "Upcoming"
        if due_date:
            current_date = datetime.utcnow()
            if isinstance(due_date, str):  # If due_date is a string, parse it to a datetime object
                try:
                    due_date = parse_datetime(due_date)
                except ValueError:
                    due_date = None  # Handle invalid date strings gracefully

            if due_date and due_date.date() == current_date.date():
                task_status = "Pending"
            elif due_date and due_date.date() < current_date.date():
                task_status = "Overdue"
        return task_status

    def get_task(self, task_id):
        """Fetch the task to be deleted."""
        return get_object_or_404(Task, id=task_id)

    def can_delete_task(self, user, organization, task):
        """Check if the task can be deleted by the user."""
        if user.is_superuser:
            return True
        return OrganizationTask.objects.filter(organization=organization, task=task).exists() or \
            OrganizationUserTask.objects.filter(organization=organization, task=task).exists()

    def permission_denied_response(self):
        """Return a permission denied response."""
        return Response(
            {"detail": "Permission denied. You cannot delete this task."},
            status=status.HTTP_403_FORBIDDEN
        )

    def get_task_history_data(self, task, reason_for_deletion, current_time):
        """Generate task history data for deletion."""
        task_history_data = []
        if task.task_history:
            task_history_data = [
                {"changes": entry.get("changes", ""), "date_time": entry['date_time']}
                for entry in task.task_history.changes_data
            ]
        task_history_data.append({
            "changes": [{"change": f"{task.assigned_by} deleted task no {task.id}. Reason: {reason_for_deletion}",
                         "file_upload": ""}],
            "date_time": current_time.strftime("%d-%m-%Y %I:%M:%S %p")
        })
        return task_history_data

    def get_linked_tasks(self, task):
        """Fetch all linked tasks excluding the current task."""
        return Task.objects.filter(task_uuid=task.task_uuid).exclude(id=task.id)

    def split_tasks_by_status(self, linked_tasks):
        """Split tasks into tasks to be deleted and tasks to be updated based on status."""
        tasks_to_delete = linked_tasks.filter(
            task_status__in=[Task.STATUS_PENDING, Task.STATUS_UPCOMING, Task.STATUS_OVERDUE, Task.STATUS_IN_PROGRESS]
        )
        tasks_to_update = linked_tasks.filter(task_status=Task.STATUS_COMPLETED)
        return tasks_to_delete, tasks_to_update

    def delete_tasks(self, tasks_to_delete, reason_for_deletion, current_time, user_organization):
        """Delete tasks and record their history."""
        for linked_task in tasks_to_delete:
            linked_task_data = self.serialize_task_data(linked_task)
            linked_task_history_data = self.get_task_history_data(linked_task, reason_for_deletion, current_time)
            self.create_deletion_history(linked_task_data, linked_task_history_data, linked_task.updated_by,
                                         user_organization, reason_for_deletion)
            linked_task.delete()

    def get_deleted_due_dates_and_periods(self, tasks_to_delete, task):
        """
        Collect deleted frequency periods and due dates in the correct format.
        """
        deleted_due_dates = self._collect_deleted_due_dates(tasks_to_delete)
        self._include_original_task_due_date(deleted_due_dates, task)

        # Directly ensure the correct format without using _ensure_correct_format
        return [deleted_due_dates] if deleted_due_dates else []

    def _collect_deleted_due_dates(self, tasks_to_delete):
        """
        Collect frequency periods and due dates from tasks to delete.
        """
        deleted_due_dates = {}
        for deleted_task in tasks_to_delete:
            if deleted_task.frequency_period and deleted_task.due_date:
                deleted_due_dates[deleted_task.frequency_period] = deleted_task.due_date.strftime('%Y-%m-%d')
        return deleted_due_dates

    def _include_original_task_due_date(self, deleted_due_dates, task):
        """
        Include the original task's frequency_period and due_date if it's not completed.
        """
        if task.frequency_period and task.due_date and task.task_status != Task.STATUS_COMPLETED:
            original_task_due_date = task.due_date.strftime('%Y-%m-%d')
            deleted_due_dates[task.frequency_period] = original_task_due_date

    def update_completed_tasks(self, tasks_to_update, deleted_due_dates, task, reason_for_deletion):
        """
        Update frequency_due_date for completed tasks by clearing matched entries.
        """
        # Include the task itself in the update if it's completed
        if task.task_status == Task.STATUS_COMPLETED:
            tasks_to_update = tasks_to_update | Task.objects.filter(id=task.id)

        # Ensure deleted_due_dates is a single dictionary (normalize)
        if isinstance(deleted_due_dates, list) and deleted_due_dates:
            deleted_due_dates = deleted_due_dates[0]

        for completed_task in tasks_to_update:
            if completed_task.frequency_due_date:
                updated_due_dates = self._clear_matched_due_dates(completed_task, deleted_due_dates)

                # Only save if there are actual changes
                if updated_due_dates != completed_task.frequency_due_date:
                    completed_task.frequency_due_date = updated_due_dates
                    completed_task.save()

    def _clear_matched_due_dates(self, completed_task, deleted_due_dates):
        """
        Loop through frequency_due_date and clear the matching due dates.
        """
        updated_due_dates = []
        for entry in completed_task.frequency_due_date:
            updated_entry = {}
            for frequency_period, due_date in entry.items():
                if frequency_period in deleted_due_dates and due_date == deleted_due_dates[frequency_period]:
                    updated_entry[frequency_period] = ""  # Clear the matching due date
                else:
                    updated_entry[frequency_period] = due_date  # Keep other due dates

            updated_due_dates.append(updated_entry)
        return updated_due_dates

    def create_deletion_history(self, task_data, task_history_data, user, organization, reason_for_deletion):
        """Create a record in DeletedTaskHistory."""
        DeletedTaskHistory.objects.create(
            task_data=task_data,
            task_history=task_history_data,
            deleted_by=user,
            organization=organization,
            reason_for_deletion=reason_for_deletion
        )

    def serialize_task_data(self, task):
        """Serialize task data."""
        task_data = {}
        for field in Task._meta.fields:
            value = getattr(task, field.name)
            if field.name == 'task_history':
                continue
            if field.name == 'created_by' or field.name == 'updated_by':
                task_data[field.name] = value.email if value else "N/A"
            elif isinstance(value, uuid.UUID):
                task_data[field.name] = str(value)
            elif isinstance(value, (datetime, date)):
                task_data[field.name] = value.strftime("%Y-%m-%d %H:%M:%S")
            else:
                task_data[field.name] = value
        return task_data

    @action(detail=True, methods=['patch'])
    def partial_update(self, request, *args, **kwargs):
        return self.update(request, partial=True, *args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def get_changes_data(self, task_history_id):
        return TaskHistory.objects.filter(id=task_history_id).first().changes_data

    def _create_folders(self, folder_names):
        for folder_name in folder_names:
            try:
                self.s3.head_object(Bucket=self.bucket_name, Key=f'{folder_name}/')
                print(f"Folder '{folder_name}' already exists in bucket '{self.bucket_name}'.")
            except self.s3.exceptions.ClientError as e:
                if e.response['Error']['Code'] == '404':
                    self.s3.put_object(Bucket=self.bucket_name, Key=f'{folder_name}/')
                    print(f"Folder '{folder_name}' created in bucket '{self.bucket_name}'.")

    def _upload_files(self, organization_ids, files, task_data):
        resource_file_s3_links = []
        task_title = task_data.task_title.replace(" ", "_")
        if files:
            resource_files_folder_name = f"Resource_Files/{task_title}_{task_data.task_uuid}"
            self._create_folders([resource_files_folder_name])
            for organization_id in organization_ids:
                organization = Organization.objects.get(id=organization_id)
                organizations_folder_name = f"Organizations/{organization.company_name}_{organization.id}"
                organizations_task_folder_name = f"Organizations/{organization.company_name}_{organization.id}/{task_title}_{task_data.task_uuid}"
                self._create_folders([organizations_folder_name, organizations_task_folder_name])

                for resource_file in files:
                    resource_file.seek(0)
                    file_content = resource_file.read()

                    resource_file_s3_link = upload_file_to_s3_folder(file_content, resource_file.name,
                                                                     resource_file.content_type,
                                                                     organizations_task_folder_name)
                    resource_file_s3_links.append(resource_file_s3_link)

            for resource_file in files:
                resource_file.seek(0)
                file_content = resource_file.read()

                upload_file_to_s3_folder(file_content, resource_file.name, resource_file.content_type,
                                         resource_files_folder_name)
        return resource_file_s3_links

    def _create_organization_task(self, organization_id, task_data, user_role, organization_user_ids):
        try:
            organization = Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            raise serializers.ValidationError({"organization_id": f"Organization with id {organization_id} not found"})

        if user_role == 'admin':
            print("user_role: admin")
            # Get all users who belong to this organization
            users_in_organization = CustomUser.objects.filter(organization=organization)

            # Create a record in OrganizationUserTask for each user in the organization
            for user in users_in_organization:
                OrganizationUserTask.objects.create(
                    organization=organization,
                    organization_user=user,
                    task=task_data,
                )

            OrganizationTask.objects.create(
                organization=organization,
                task=task_data,
            )
        elif user_role == 'CCO':
            print("user_role: CCO")
            for org_user_id in organization_user_ids:
                org_user = CustomUser.objects.get(id=org_user_id)
                OrganizationUserTask.objects.create(
                    organization=organization,
                    organization_user=org_user,
                    task=task_data,
                )

    @action(detail=False, methods=['get'], url_path='org-tasks')
    def get_org_tasks(self, request):
        user = request.user
        current_year = datetime.now().year

        # Helper function to get tasks for the logged-in user (CCO role)
        def get_tasks_for_ccos(user):
            # Fetch the organization of the logged-in CCO user
            user_organization = user.organization

            # Filter tasks for the current year assigned to the user's organization or any user within the organization
            return Task.objects.filter(
                Q(due_date__year=current_year) &  # Filter by current year
                (
                        Q(organizationtask__organization=user_organization) |  # Tasks assigned to their org via OrganizationTask
                        Q(organizationusertask__organization=user_organization)
                    # Tasks assigned to any user within their org
                )
            ).distinct()  # Ensure unique tasks

        # If the user is a CCO, get tasks based on the organization
        if user.role == 'CCO':
            tasks = get_tasks_for_ccos(user)  # Get full task objects
        else:
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        if not tasks:
            return Response({"detail": "No tasks found for this organization."}, status=status.HTTP_404_NOT_FOUND)

        # Serialize the tasks to include all fields
        serializer = OrgTaskSerializer(tasks, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class TaskHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TaskHistory.objects.all()
    serializer_class = TaskHistorySerializer
    permission_classes = [IsAuthenticated]
    swagger_schema = TaskSwaggerAutoSchema

    def get_queryset(self):
        task_id = self.request.query_params.get('task_id')
        if task_id is not None:
            return self.queryset.filter(task__id=task_id)
        return self.queryset


class ArchiveTasksPagination(PageNumberPagination):
    page_size = 10  # Default page size is 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class ArchiveTasksView(APIView):
    permission_classes = [IsAuthenticated]
    swagger_schema = TaskSwaggerAutoSchema
    pagination_class = ArchiveTasksPagination

    @swagger_auto_schema(
        operation_description="Fetch tasks and deleted task histories (70% tasks, 30% deleted task histories) "
                              "for the given page and page size. Optionally filter by task title using 'search_by_title'.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'search_by_title': openapi.Schema(type=openapi.TYPE_STRING, description="Title to search for in tasks")
            },
            required=[]  # It's an optional field
        ),
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number for pagination",
                              type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="Number of results per page",
                              type=openapi.TYPE_INTEGER, default=10)
        ]
    )
    def post(self, request, *args, **kwargs):
        try:
            # Get the optional search term from the request body
            search_by_title = request.data.get('search_by_title', '').strip()

            # Pagination variables
            page_number = int(request.query_params.get('page', 1))  # Get the page number from query params
            page_size = int(request.query_params.get('page_size', self.pagination_class.page_size))  # Get page size

            # Filter Tasks by title (Partial match using icontains)
            tasks_query = Task.objects.all().select_related('created_by', 'updated_by', 'task_history').order_by(
                '-updated_at')
            # Filter DeletedTaskHistories by task_title in the task_data JSON field (partial match)
            partial_title_tasks = tasks_query.filter(
                task_title__icontains=search_by_title) if search_by_title else tasks_query

            # Filter DeletedTaskHistories by task_title in the task_data JSON field (Partial match)
            deleted_task_histories_query = DeletedTaskHistory.objects.all().select_related('deleted_by').order_by(
                '-deleted_at')

            deleted_partial_title_tasks = deleted_task_histories_query.filter(
                task_data__task_title__icontains=search_by_title) if search_by_title else deleted_task_histories_query

            # Extract task_ids from deleted task histories to filter out from the main task query
            deleted_task_ids = set(
                deleted_partial_title_tasks.values_list('task_data__task_id', flat=True)
            )

            # Remove tasks that are already present in deleted_task_histories_query based on task_id
            tasks_query = [task for task in partial_title_tasks if task.id not in deleted_task_ids]
            deleted_task_histories_query = list(deleted_partial_title_tasks)

            # Get the counts of matching records from both models
            total_tasks_count = len(tasks_query)
            total_deleted_task_histories_count = len(deleted_task_histories_query)

            # Handle pagination
            if search_by_title:
                total_records = total_tasks_count + total_deleted_task_histories_count

                # If the total records from both models are less than the page_size, use all available records
                if total_records < page_size:
                    tasks_limit = total_tasks_count
                    deleted_task_histories_limit = total_deleted_task_histories_count
                else:
                    tasks_limit = min(total_tasks_count, page_size)
                    deleted_task_histories_limit = page_size - tasks_limit

                paginated_tasks = tasks_query[:tasks_limit]
                paginated_deleted_task_histories = deleted_task_histories_query[:deleted_task_histories_limit]

            else:
                # Default behavior when `search_by_title` is an empty string or not provided
                task_limit = (page_size * 70) // 100  # 70% of page size
                deleted_task_history_limit = page_size - task_limit  # Remaining 30% for deleted tasks

                # Ensure you fetch enough records to satisfy the page_size
                task_offset = (page_number - 1) * task_limit
                deleted_task_history_offset = (page_number - 1) * deleted_task_history_limit

                # Adjust for cases where one model doesn't have enough records
                paginated_tasks = tasks_query[task_offset:task_offset + task_limit]
                remaining_task_count = page_size - len(paginated_tasks)
                if remaining_task_count > 0:
                    paginated_deleted_task_histories = deleted_task_histories_query[
                                                       deleted_task_history_offset:deleted_task_history_offset + remaining_task_count]
                else:
                    paginated_deleted_task_histories = deleted_task_histories_query[
                                                       deleted_task_history_offset:deleted_task_history_offset + deleted_task_history_limit]

            # Combine tasks and deleted task histories based on updated_at and deleted_at
            combined_list = sorted(
                list(paginated_tasks) + list(paginated_deleted_task_histories),
                key=lambda x: getattr(x, 'updated_at', getattr(x, 'deleted_at', None)),
                reverse=True
            )

            # Serialize the combined list
            serializer = TaskWithDeletedHistorySerializer(combined_list, many=True)

            # Prepare the response data
            response_data = {
                "total_records": total_tasks_count + total_deleted_task_histories_count,
                "archive_tasks": serializer.data
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
