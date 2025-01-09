import json
import uuid
from decouple import config
from datetime import datetime

from urllib.parse import urlparse

from django.utils.dateparse import parse_datetime
from rest_framework import serializers
from dateutil.relativedelta import relativedelta

from accounts.models import CustomUser
from organization.models import Organization
from rest_framework.exceptions import ValidationError
from utils.s3_utils import upload_file_to_s3_folder, initialize_s3_client
from .models import Task, OrganizationTask, TaskHistory, OrganizationUserTask, DeletedTaskHistory


class OrgTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'


class TaskSerializer(serializers.ModelSerializer):
    # Direct model fields
    resource_file_s3_links = serializers.JSONField(default=list, required=False)
    task_status = serializers.ChoiceField(choices=Task.STATUS_CHOICES, required=False)
    frequency_due_date = serializers.JSONField(default=list, required=False)
    template_json_data = serializers.CharField(required=False, allow_null=True)
    user_list = serializers.JSONField(default=list, required=False)

    # Extra input-only fields
    organization_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=True
    )
    organization_user_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    changes_data = serializers.JSONField(default=list, write_only=True)

    # File upload fields
    s3_file_1 = serializers.FileField(required=False, allow_null=True, write_only=True)
    s3_file_2 = serializers.FileField(required=False, allow_null=True, write_only=True)
    file_1 = serializers.FileField(required=False, allow_null=True, write_only=True)
    file_2 = serializers.FileField(required=False, allow_null=True, write_only=True)
    file_3 = serializers.FileField(required=False, allow_null=True, write_only=True)
    file_4 = serializers.FileField(required=False, allow_null=True, write_only=True)
    file_5 = serializers.FileField(required=False, allow_null=True, write_only=True)
    task_report_file = serializers.FileField(required=False, allow_null=True, write_only=True)
    is_s3_file_1_empty = serializers.BooleanField(default=False, write_only=True)
    is_s3_file_2_empty = serializers.BooleanField(default=False, write_only=True)
    is_resource_link_empty = serializers.BooleanField(default=False, write_only=True)
    is_bulk_edit = serializers.BooleanField(default=False, required=False)

    s3 = initialize_s3_client()
    bucket_name = config('S3_BUCKET_NAME')

    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['frequency_period', 'due_date', 'task_history', 'created_by', 'updated_by', 'created_at',
                            'assigned_by', 'updated_at']

    def validate_resource_file_s3_links(self, value):
        if not isinstance(value, list):
            raise ValidationError("resource_file_s3_links must be a list.")
        for item in value:
            self._validate_resource_item(item)
        return value

    def _validate_resource_item(self, item):
        if not isinstance(item, dict):
            raise ValidationError("Each item in resource_file_s3_links must be a dictionary.")
        self._validate_required_keys(item, ['file_link', 'file_name'])
        file_link = item['file_link']
        if not isinstance(file_link, dict):
            raise ValidationError("'file_link' must be a dictionary.")
        self._validate_required_keys(file_link, ['preview_link', 'download_link'])
        # Relaxed URL validation
        self._validate_url_format(file_link['preview_link'])
        self._validate_url_format(file_link['download_link'])
        if not isinstance(item['file_name'], str):
            raise ValidationError("'file_name' must be a string.")

    def _validate_url_format(self, url):
        """
        Validates the URL format, allowing query parameters and special characters.
        """
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                raise ValidationError(f"Invalid URL format: {url}")
        except Exception:
            raise ValidationError(f"Invalid URL format: {url}")

    def _validate_required_keys(self, dictionary, keys):
        for key in keys:
            if key not in dictionary:
                raise ValidationError(f"Each dictionary in resource_file_s3_links must contain '{key}' key.")

    def _validate_urls(self, urls, url_validator):
        for url in urls:
            try:
                url_validator(url)
            except ValidationError:
                raise ValidationError(f"Invalid URL: {url}")

    def validate_user_list(self, value):
        # Handle JSON string conversion
        if isinstance(value, str):
            try:
                value = json.loads(value)  # Convert JSON string to a list
            except json.JSONDecodeError:
                raise serializers.ValidationError("user_list must be a valid JSON string or list.")

        # Validate that it is a list
        if not isinstance(value, list):
            raise serializers.ValidationError("user_list must be a list.")

        # Ensure all items in the list are strings
        if not all(isinstance(item, str) for item in value):
            raise serializers.ValidationError("Each item in user_list must be a string.")

        return value

    def validate_changes_data(self, value):
        if not isinstance(value, list):
            raise ValidationError("changes_data must be a list.")
        for item in value:
            if not isinstance(item, dict):
                raise ValidationError("Each item in changes_data must be a dictionary.")
            if "changes" not in item:
                raise ValidationError("Each item in changes_data must contain 'changes' key.")
            if not isinstance(item['changes'], list):
                raise ValidationError("The 'changes' value must be a list.")
        return value

    def validate_frequency_due_date(self, value):
        frequency = self.initial_data.get('frequency')

        # Convert JSON string to list if needed
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise ValidationError("frequency_due_date must be a valid JSON string or list.")

        if not isinstance(value, list) or not value:
            raise ValidationError("frequency_due_date must be a non-empty list.")

        if frequency == 'Quarterly':
            self._validate_quarterly(value)
        elif frequency == 'Monthly':
            self._validate_monthly(value)
        elif frequency == 'Twice a Year':
            self._validate_twice_a_year(value)
        elif frequency == 'Yearly':
            self._validate_yearly(value)
        else:
            raise ValidationError(f"Unsupported frequency: {frequency}")

        return value

    def _validate_quarterly(self, value):
        expected_keys = {'Q1', 'Q2', 'Q3', 'Q4'}
        self._validate_single_dict(value, expected_keys, "Quarterly")

    def _validate_monthly(self, value):
        self._validate_single_dict(value, {'month'}, "Monthly")

    def _validate_twice_a_year(self, value):
        expected_keys = {'first_half_year', 'second_half_year'}
        self._validate_single_dict(value, expected_keys, "Twice a Year")

    def _validate_yearly(self, value):
        self._validate_single_dict(value, {'year'}, "Yearly")

    def _validate_single_dict(self, value, expected_keys, frequency):
        if len(value) != 1 or not isinstance(value[0], dict):
            raise ValidationError(
                f"frequency_due_date must be a list containing a single dictionary with keys: {', '.join(expected_keys)} for {frequency} frequency."
            )

        data_dict = value[0]
        if set(data_dict.keys()) != expected_keys:
            raise ValidationError(
                f"frequency_due_date dictionary must contain keys: {', '.join(expected_keys)} for {frequency} frequency."
            )

        for date_str in data_dict.values():
            if not self._is_valid_date(date_str):
                raise ValidationError(f"Invalid date format in frequency_due_date: {date_str}.")

    def _is_valid_date(self, date_str):
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def validate_organization_ids(self, value):
        return self._validate_list_of_integers(value, 'organization_ids')

    def validate_organization_user_ids(self, value):
        return self._validate_list_of_integers(value, 'organization_user_ids')

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
        request = self.context.get('request')
        user = request.user
        assigned_by = 'admin' if user.is_superuser else 'cco'
        validated_data['created_by'] = user
        validated_data['updated_by'] = user
        validated_data['assigned_by'] = assigned_by
        validated_data.pop('organization_ids', [])
        validated_data.pop('organization_user_ids', [])
        validated_data.pop('is_s3_file_1_empty', False)
        validated_data.pop('is_s3_file_2_empty', False)
        validated_data.pop('is_resource_link_empty', False)
        validated_data.pop('changes_data', [])
        validated_data.pop('file_1', "")
        validated_data.pop('file_2', "")
        validated_data.pop('file_3', "")
        validated_data.pop('file_4', "")
        validated_data.pop('file_5', "")
        validated_data.pop('is_bulk_edit', "")
        validated_data.pop('task_report_file', "")
        s3_file_1 = validated_data.pop('s3_file_1', "")
        s3_file_2 = validated_data.pop('s3_file_2', "")
        s3_files = [file for file in [s3_file_1, s3_file_2] if file]
        frequency = validated_data.get('frequency', "Yearly")
        frequency_due_date = validated_data.get('frequency_due_date', [])

        if s3_files:
            uploaded_s3_file_links = self._upload_task_resource_file(s3_files)
            validated_data['s3_file_links'] = uploaded_s3_file_links

        all_task_data = self._create_tasks_based_on_frequency(validated_data, frequency, frequency_due_date)

        return all_task_data

    def _create_tasks_based_on_frequency(self, validated_data, frequency, frequency_due_date):
        all_task_data = []
        print(frequency)
        if frequency == 'Quarterly':
            all_task_data = self._create_quarterly_tasks(validated_data, frequency_due_date)
        elif frequency == 'Monthly':
            all_task_data = self._create_monthly_tasks(validated_data, frequency_due_date)
        elif frequency == 'Twice a Year':
            all_task_data = self._create_twice_a_year_tasks(validated_data, frequency_due_date)
        elif frequency == 'Yearly':
            all_task_data = self._create_yearly_tasks(validated_data, frequency_due_date)

        return all_task_data

    def _create_quarterly_tasks(self, validated_data, frequency_due_date):
        return self._create_tasks_for_due_dates(validated_data, frequency_due_date[0].items())

    def _create_monthly_tasks(self, validated_data, frequency_due_date):
        start_date_str = frequency_due_date[0]["month"]
        monthly_due_dates = self._generate_monthly_due_dates(start_date_str)
        return self._create_tasks_for_due_dates(validated_data, [('month', due_date) for due_date in monthly_due_dates])

    def _create_twice_a_year_tasks(self, validated_data, frequency_due_date):
        return self._create_tasks_for_due_dates(validated_data, frequency_due_date[0].items())

    def _create_yearly_tasks(self, validated_data, frequency_due_date):
        return self._create_tasks_for_due_dates(validated_data, frequency_due_date[0].items())

    def _create_tasks_for_due_dates(self, validated_data, due_dates):
        tasks = []

        # Fetch existing task_uuid from validated_data or instance
        task_uuid = validated_data.get('task_uuid')
        print("existing:", task_uuid)
        if not task_uuid:
            task_uuid = uuid.uuid4()
            validated_data['task_uuid'] = task_uuid

        for frequency_period, due_date in due_dates:
            if due_date:
                validated_data['due_date'] = due_date
                validated_data['frequency_period'] = frequency_period

                # Only set frequency_due_date if the frequency is "monthly"
                if validated_data.get('frequency') == 'Monthly':
                    validated_data['frequency_due_date'] = [{'month': due_date}]

                task = Task.objects.create(**validated_data)
                tasks.append(task)

        return tasks

    def _generate_monthly_due_dates(self, start_date_str):
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        start_day = start_date.day

        due_dates = [start_date]
        current_date = start_date

        while current_date.year == start_date.year:
            next_date = current_date + relativedelta(months=1)
            try:
                next_date = next_date.replace(day=start_day)
            except ValueError:
                next_date = next_date + relativedelta(day=31)

            if next_date.year == start_date.year:
                due_dates.append(next_date)
            current_date = next_date

        return [date.strftime("%Y-%m-%d") for date in due_dates]

    def update(self, instance, validated_data):
        frequency_due_date = validated_data.get('frequency_due_date', [])
        request = self.context.get('request')
        user = request.user
        assigned_by = 'admin' if user.is_superuser else 'cco'
        validated_data['created_by'] = user
        validated_data['updated_by'] = user
        validated_data['assigned_by'] = assigned_by
        organization_ids = validated_data.pop('organization_ids', [])
        file_1 = validated_data.pop('file_1', "")
        file_2 = validated_data.pop('file_2', "")
        file_3 = validated_data.pop('file_3', "")
        file_4 = validated_data.pop('file_4', "")
        file_5 = validated_data.pop('file_5', "")
        s3_file_1 = validated_data.pop('s3_file_1', "")
        s3_file_2 = validated_data.pop('s3_file_2', "")

        files = [file for file in [file_1, file_2, file_3, file_4, file_5] if file]
        resource_file_s3_links = validated_data.get('resource_file_s3_links', [])
        is_resource_link_empty = validated_data.pop('is_resource_link_empty', False)
        is_s3_file_1_empty = validated_data.pop('is_s3_file_1_empty', False)
        is_s3_file_2_empty = validated_data.pop('is_s3_file_2_empty', False)
        changes_data = validated_data.pop('changes_data', [])
        organization_user_ids = validated_data.pop('organization_user_ids', [])
        user_list = validated_data.pop('user_list', [])
        frequency = validated_data.get('frequency', instance.frequency)
        task_report_file = validated_data.pop('task_report_file', "")
        validated_data['updated_by'] = user
        is_bulk_edit = validated_data.pop('is_bulk_edit', "")
        created_tasks = []
        frequency_changed = frequency != instance.frequency
        not_task_delete = False
        no_missing_due_dates = True
        instance_delete = False

        # Handle frequency changes early
        if frequency_changed:
            try:
                # Delete incomplete tasks related to the old frequency
                self.delete_incomplete_tasks_by_id(instance.id, user)

                # If instance was deleted, set it to None
                if not Task.objects.filter(id=instance.id).exists():
                    instance = None
                    instance_delete = True
                else:
                    not_task_delete = True

            except Exception as e:
                instance = None

            # Create new tasks based on the new frequency_due_date
            if frequency_due_date:
                created_tasks = self._create_tasks_based_on_frequency(
                    validated_data,
                    validated_data.get('frequency', 'Yearly'),
                    frequency_due_date
                )

        if instance_delete is False and frequency_due_date:
            # Call the new function to check for missing due dates
            has_missing_due_dates = self.has_missing_due_dates(instance, frequency_due_date)
            if not frequency_changed and has_missing_due_dates:
                created_tasks = self.handle_missing_due_dates(instance, validated_data, frequency_due_date)
                no_missing_due_dates = False

        if instance and not_task_delete is False and no_missing_due_dates is True:
            if changes_data:
                current_utc_time = datetime.utcnow().strftime('%d-%m-%Y %H:%M:%S %p')
                changes_data[0]["date_time"] = current_utc_time

            user_role, existing_tasks = self._get_user_role_and_tasks(user, instance)
            existing_resource_file_s3_links = instance.resource_file_s3_links

            all_resource_file_s3_links = self._handle_files_and_links(files, resource_file_s3_links, organization_ids,
                                                                      instance, existing_resource_file_s3_links)

            existing_s3_file_links = instance.s3_file_links or []
            s3_file_links_dict = {list(d.keys())[0]: d[list(d.keys())[0]] for d in existing_s3_file_links}

            if is_s3_file_1_empty:
                s3_file_links_dict.pop("s3_file_1", None)
            if is_s3_file_2_empty:
                s3_file_links_dict.pop("s3_file_2", None)

            resource_files_folder = "task_resource_files"
            self._create_folders([resource_files_folder])

            if s3_file_1:
                uploaded_file_link = upload_file_to_s3_folder(
                    s3_file_1.read(),
                    s3_file_1.name,
                    s3_file_1.content_type,
                    resource_files_folder
                )
                s3_file_links_dict["s3_file_1"] = uploaded_file_link

            if s3_file_2:
                uploaded_file_link = upload_file_to_s3_folder(
                    s3_file_2.read(),
                    s3_file_2.name,
                    s3_file_2.content_type,
                    resource_files_folder
                )
                s3_file_links_dict["s3_file_2"] = uploaded_file_link

            validated_data['s3_file_links'] = [{key: value} for key, value in s3_file_links_dict.items()]

            if is_resource_link_empty:
                validated_data['resource_file_s3_links'] = []
            else:
                validated_data['resource_file_s3_links'] = all_resource_file_s3_links

            if user_role == 'admin':
                self._process_admin_role(organization_ids, existing_tasks, instance, organization_user_ids, user_role)
            elif user_role == 'CCO':
                self._process_cco_role(organization_user_ids, existing_tasks, organization_ids, instance)

            self._update_due_dates_for_related_tasks(instance, frequency_due_date)
            self._update_task_history(instance, changes_data)
            self._update_instance_fields(instance, validated_data)
            self._update_task_status(instance)
            instance.save()
            self._update_task_report_users(instance, user_list, task_report_file)
            if is_bulk_edit is True:
                if user_role == 'CCO':
                    self._process_cco_role_related_task(organization_user_ids, existing_tasks, organization_ids,
                                                        instance, user_role)
                self._update_all_related_tasks(instance, validated_data)

        return instance, created_tasks

    def delete_incomplete_tasks_by_id(self, task_id, user):
        """
        Deletes incomplete tasks by task_id and updates related tasks' frequency_due_date.
        """
        try:
            # Fetch the task by ID and user
            task = Task.objects.get(id=task_id, created_by=user)
            task_uuid = task.task_uuid
            task_due_date, task_frequency = self._prepare_task_data(task)

            # Check if the task is completed
            if task.task_status != Task.STATUS_COMPLETED:
                task.delete()
            else:
                print(f"Task ID {task_id} is completed and will not be deleted.")

            # Fetch all related tasks
            related_tasks = Task.objects.filter(task_uuid=task_uuid, created_by=user)
            incomplete_due_dates = self._collect_incomplete_due_dates(related_tasks, task_due_date, task_frequency)

            # Delete incomplete related tasks
            related_tasks.exclude(task_status=Task.STATUS_COMPLETED).delete()

            # Update completed tasks' due dates
            self._update_completed_tasks_due_dates(related_tasks, incomplete_due_dates)

        except Task.DoesNotExist:
            raise serializers.ValidationError(
                {"error": f"Task with id {task_id} does not exist or does not belong to the user."}
            )

    def _prepare_task_data(self, task):
        """
        Prepare task data for further processing (due date and frequency period).
        Only get the due date if the task is not completed.
        """
        if task.task_status != Task.STATUS_COMPLETED:
            task_due_date = task.due_date.strftime('%Y-%m-%d') if task.due_date else None
        else:
            task_due_date = None

        task_frequency = task.frequency_period
        return task_due_date, task_frequency

    def _collect_incomplete_due_dates(self, related_tasks, task_due_date, task_frequency):
        """
        Collect due dates and frequency periods from incomplete tasks only.
        """
        incomplete_due_dates = {
            task.due_date.strftime('%Y-%m-%d'): task.frequency_period
            for task in related_tasks.exclude(task_status=Task.STATUS_COMPLETED)
            if task.due_date
        }

        if task_due_date:
            incomplete_due_dates[task_due_date] = task_frequency

        return incomplete_due_dates

    def _update_completed_tasks_due_dates(self, related_tasks, incomplete_due_dates):
        """
        Update frequency_due_date for completed tasks if necessary.
        """
        for completed_task in related_tasks.filter(task_status=Task.STATUS_COMPLETED):
            if completed_task.frequency_due_date:
                updated_due_dates = self._clear_matched_due_dates(completed_task, incomplete_due_dates)

                # Only save if there are actual changes
                if updated_due_dates != completed_task.frequency_due_date:
                    completed_task.frequency_due_date = updated_due_dates
                    completed_task.save()

    def _clear_matched_due_dates(self, completed_task, incomplete_due_dates):
        """
        Clear the matched due dates from completed tasks' frequency_due_date.
        """
        updated_due_dates = []
        for entry in completed_task.frequency_due_date:
            updated_entry = {}
            for frequency_period, due_date in entry.items():
                if due_date in incomplete_due_dates and frequency_period == incomplete_due_dates[due_date]:
                    updated_entry[frequency_period] = ""  # Clear the matching due date
                else:
                    updated_entry[frequency_period] = due_date
            updated_due_dates.append(updated_entry)
        return updated_due_dates

    def has_missing_due_dates(self, instance, frequency_due_date):
        """
        Check if there are missing due dates in the instance compared to the payload.
        Returns True if any due dates are missing, otherwise False.
        """
        existing_due_dates = instance.frequency_due_date[0]
        payload_due_dates = frequency_due_date[0]

        # Check if any due date in the existing_due_dates is empty while the corresponding payload_due_date is provided
        for key, existing_date in existing_due_dates.items():
            if not existing_date and key in payload_due_dates and payload_due_dates[key]:
                return True

        return False

    def _update_all_related_tasks(self, instance, validated_data):
        """
        Updates all related tasks with the same task_uuid, updates their fields,
        and calculates their task_status, excluding tasks with 'Completed' or 'In Progress' status.
        """
        # Fetch related tasks excluding the current instance
        related_tasks = Task.objects.filter(task_uuid=instance.task_uuid).exclude(id=instance.id)

        current_date = datetime.utcnow().date()  # Current UTC date

        for task in related_tasks:
            # Skip tasks with status 'Completed' or 'In Progress'
            if task.task_status in ["Completed", "In Progress"]:
                continue

            # Step 1: Update fields from validated_data (excluding task_status, answer_data, frequency_due_date, and due_date for Monthly tasks)
            for field, value in validated_data.items():
                if hasattr(task, field) and field not in ["task_status", "answer_data"]:
                    # Exclude 'frequency_due_date' and 'due_date' if the frequency is 'Monthly'
                    if task.frequency == Task.FREQUENCY_MONTHLY and field in ["frequency_due_date", "due_date"]:
                        continue
                    setattr(task, field, value)

            # Step 2: Update task status based on due_date
            due_date = task.due_date
            if due_date:
                if isinstance(due_date, str):
                    due_date = parse_datetime(due_date).date()

                if due_date:
                    if due_date == current_date:
                        task_status = "Pending"
                    elif due_date < current_date:
                        task_status = "Overdue"
                    else:
                        task_status = "Upcoming"

                    # Assign the calculated task status
                    task.task_status = task_status

            # Step 3: Persist changes to the database
            task.save()

        return instance

    def _update_task_status(self, instance):
        """
        Updates the task status of the instance based on the current due date and the current date.
        """
        current_date = datetime.utcnow().date()
        due_date = instance.due_date

        if instance.task_status == "In Progress" or instance.task_status == "Completed":
            return

        if due_date:
            if isinstance(due_date, str):
                due_date = parse_datetime(due_date).date()

            if due_date == current_date:
                instance.task_status = "Pending"
            elif due_date < current_date:
                instance.task_status = "Overdue"
            else:
                instance.task_status = "Upcoming"

        # Save the instance to persist the task status
        instance.save(update_fields=["task_status"])  # Save only task_status to the database

    def handle_missing_due_dates(self, instance, validated_data, frequency_due_date):
        """
        Orchestrate updating the instance, related tasks, and creating new tasks for missing due dates.
        """
        # Extract task_uuid and payload_due_dates
        task_uuid = instance.task_uuid
        payload_due_dates = frequency_due_date[0]
        existing_due_dates = instance.frequency_due_date

        # Step 1: Update the instance's frequency_due_date
        self._update_instance_due_dates(instance, payload_due_dates)

        # Step 2: Update related completed tasks
        self._update_related_completed_tasks(task_uuid, payload_due_dates)

        # Step 3: Identify missing due dates
        missing_due_dates = self._get_missing_due_dates(existing_due_dates, payload_due_dates)

        # Step 4: Create new tasks for missing due dates
        new_tasks = []
        if missing_due_dates:
            validated_data['task_uuid'] = task_uuid
            new_tasks = self._create_tasks_based_on_frequency(validated_data, instance.frequency, [missing_due_dates])
        return new_tasks

    def _update_instance_due_dates(self, instance, payload_due_dates):
        """
        Update the instance's frequency_due_date with the payload's frequency_due_date.
        """
        instance.frequency_due_date = [payload_due_dates]
        instance.save()
        print("Instance frequency_due_date updated.")

    def _update_related_completed_tasks(self, task_uuid, payload_due_dates):
        """
        Update frequency_due_date for tasks with the same task_uuid and 'Completed' status.
        """
        related_tasks = Task.objects.filter(task_uuid=task_uuid, task_status=Task.STATUS_COMPLETED)
        print(f"Found {related_tasks.count()} related tasks with 'Completed' status.")

        for task in related_tasks:
            task.frequency_due_date = [payload_due_dates]
            task.save()
            print(f"Updated frequency_due_date for task with ID: {task.id}")

    def _get_missing_due_dates(self, existing_due_dates, payload_due_dates):
        """
        Compare existing due dates with payload due dates and return missing entries.
        """
        missing_due_dates = {
            key: payload_due_dates[key]
            for key, date in existing_due_dates[0].items()
            if not date and key in payload_due_dates and payload_due_dates[key]
        }
        return missing_due_dates

    def _update_due_dates_for_related_tasks(self, instance, frequency_due_date):
        # Only proceed if frequency is Quarterly or Twice a Year
        if instance.frequency in [Task.FREQUENCY_QUARTERLY, Task.FREQUENCY_TWICE_A_YEAR]:
            # Get all tasks with the same `task_uuid`, including the current instance
            related_tasks = Task.objects.filter(task_uuid=instance.task_uuid)

            # Define a mapping between frequency periods and their due dates from the payload
            due_date_mapping = frequency_due_date[0] if frequency_due_date else {}

            for task in related_tasks:
                # Check if the task's frequency period exists in the due date mapping

                period_key = task.frequency_period
                if period_key in due_date_mapping:
                    # Update the task's due_date and frequency_due_date fields
                    task.due_date = due_date_mapping[period_key]
                    task.frequency_due_date = frequency_due_date
                    task.save()

            # Update the due_date and frequency_due_date of the current task (instance) explicitly
            instance.frequency_due_date = frequency_due_date
            if instance.frequency_period in due_date_mapping:
                instance.due_date = due_date_mapping[instance.frequency_period]
            instance.save()

        else:
            # For Monthly and Yearly frequencies, only update the current task's due_date
            if frequency_due_date and isinstance(frequency_due_date[0], dict):
                period_key = 'month' if instance.frequency == Task.FREQUENCY_MONTHLY else 'year'
                instance.due_date = frequency_due_date[0].get(period_key)
                instance.frequency_due_date = frequency_due_date
                instance.save()

    def _process_admin_role(self, organization_ids, existing_tasks, instance, organization_user_ids, user_role):
        """
        Handles assignment and unassignment of OrganizationTask and OrganizationUserTask
        based on the organization_ids provided in the payload.
        """
        existing_organization_ids = list(existing_tasks.values_list('organization_id', flat=True))

        # Determine IDs to add and remove
        ids_to_add = set(organization_ids) - set(existing_organization_ids)
        ids_to_remove = set(existing_organization_ids) - set(organization_ids)

        # Unassign removed tasks
        self._unassign_organization_tasks(ids_to_remove, existing_tasks)

        # Assign new tasks
        self._assign_organization_tasks(ids_to_add, instance)

    def _unassign_organization_tasks(self, ids_to_remove, existing_tasks):
        """
        Unassign tasks for removed organization_ids.
        Deletes OrganizationTask and related OrganizationUserTask entries.
        """
        for org_id in ids_to_remove:
            organization_task = existing_tasks.filter(organization_id=org_id).first()
            if organization_task:
                # Remove all associated OrganizationUserTask entries
                OrganizationUserTask.objects.filter(task=organization_task.task).delete()
                # Remove OrganizationTask
                organization_task.delete()

    def _assign_organization_tasks(self, ids_to_add, instance):
        """
        Assign tasks for new organization_ids.
        Creates OrganizationTask and related OrganizationUserTask entries.
        """
        for org_id in ids_to_add:
            organization = self._get_organization(org_id)
            organization_task, created = OrganizationTask.objects.get_or_create(
                organization=organization,
                task=instance
            )

            if created:
                # Fetch all users associated with the organization
                organization_users = CustomUser.objects.filter(organization=organization)
                for user in organization_users:
                    OrganizationUserTask.objects.get_or_create(
                        organization=organization,
                        organization_user=user,
                        task=instance
                    )

    def _process_cco_role(self, organization_user_ids, existing_tasks, organization_ids, instance):
        """
        Process task assignments and removals for organization users based on updates.
        """
        # Step 1: Fetch existing and updated user IDs
        existing_user_ids = set(existing_tasks.values_list('organization_user_id', flat=True))
        if not isinstance(organization_user_ids, (list, tuple)):
            organization_user_ids = [organization_user_ids]
        updated_user_ids = set(organization_user_ids)

        # Step 2: Assign tasks to new users
        self._assign_tasks_to_new_users(existing_tasks, updated_user_ids, existing_user_ids, organization_ids, instance)

        # Step 3: Remove tasks from users no longer assigned
        self._remove_tasks_from_extra_users(existing_tasks, existing_user_ids, updated_user_ids)

    def _assign_tasks_to_new_users(self, existing_tasks, updated_user_ids, existing_user_ids, organization_ids,
                                   instance):
        """
        Assign tasks to new users who don't have them already.
        """
        new_user_ids = updated_user_ids - existing_user_ids
        for organization_user in new_user_ids:
            # Double-check to avoid race condition or duplicate task
            if not existing_tasks.filter(organization_user_id=organization_user).exists():
                self._create_organization_task(organization_ids[0], instance, [organization_user])
            else:
                print(f"Task already exists for user ID: {organization_user}, skipping creation.")

    def _remove_tasks_from_extra_users(self, existing_tasks, existing_user_ids, updated_user_ids):
        """
        Remove tasks from users no longer part of the updated list.
        """
        extra_user_ids = existing_user_ids - updated_user_ids
        for extra_user_id in extra_user_ids:
            extra_task = existing_tasks.filter(organization_user_id=extra_user_id).first()
            if extra_task:
                extra_task.delete()

    def _process_cco_role_related_task(self, organization_user_ids, existing_tasks, organization_ids, instance,
                                       user_role):
        # Step 1: Get the task UUID from the instance and fetch tasks
        task_uuid = instance.task_uuid
        tasks = Task.objects.filter(task_uuid=task_uuid)

        # Step 2: Fetch existing user IDs from the OrganizationUserTask model
        existing_user_ids = set(OrganizationUserTask.objects.values_list('organization_user__id', flat=True))

        # Step 3: Normalize and get updated user IDs
        updated_user_ids = self._normalize_user_ids(organization_user_ids)

        # Step 4: Assign tasks to new users
        self._assign_tasks_to_related_new_users(updated_user_ids, existing_user_ids, tasks, organization_ids, user_role)

        # Step 5: Remove tasks from users who no longer need them
        self._remove_tasks_from_old_users(updated_user_ids, existing_user_ids, tasks)

    def _normalize_user_ids(self, organization_user_ids):
        """
        Ensure organization_user_ids is a list, and return updated user IDs as a set.
        """
        if not isinstance(organization_user_ids, (list, tuple)):
            organization_user_ids = [organization_user_ids]
        updated_user_ids = set(organization_user_ids)
        return updated_user_ids

    def _assign_tasks_to_related_new_users(self, updated_user_ids, existing_user_ids, tasks, organization_ids,
                                           user_role):
        """
        Assign tasks to users who don't already have them.
        """
        new_user_ids = updated_user_ids - existing_user_ids

        for organization_user_id in updated_user_ids:
            for task in tasks:
                task_exists_for_user = OrganizationUserTask.objects.filter(
                    task=task, organization_user_id=organization_user_id).exists()

                if not task_exists_for_user:
                    self._create_organization_task(organization_ids[0], task, [organization_user_id])
                else:
                    print(
                        f"Task {task.task_uuid} already assigned to user ID: {organization_user_id}, skipping assignment.")

    def _remove_tasks_from_old_users(self, updated_user_ids, existing_user_ids, tasks):
        """
        Remove tasks from users who are no longer assigned to them.
        """
        remove_user_ids = existing_user_ids - updated_user_ids

        for user_id in remove_user_ids:
            for task in tasks:
                task_to_remove = OrganizationUserTask.objects.filter(
                    task=task, organization_user_id=user_id).first()
                if task_to_remove:
                    task_to_remove.delete()

    def _update_instance_fields(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

    def _get_user_role_and_tasks(self, user, instance):
        global user_role, existing_tasks
        if user.is_superuser:
            user_role = 'admin'
            existing_tasks = instance.organizationtask_set.all()
        elif user.role == 'CCO':
            user_role = 'CCO'
            existing_tasks = instance.organizationusertask_set.all()
        return user_role, existing_tasks

    def _get_organization(self, organization_id):
        try:
            return Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            raise serializers.ValidationError({"organization_id": f"Organization with id {organization_id} not found"})

    def _create_organization_task(self, organization_id, task_data, organization_user_ids):
        organization = self._get_organization(organization_id)
        for org_user_id in organization_user_ids:
            org_user = CustomUser.objects.get(id=org_user_id)
            OrganizationUserTask.objects.create(
                organization=organization,
                organization_user=org_user,
                task=task_data,
            )

    def _handle_files_and_links(self, files, resource_file_s3_links, organization_ids, instance,
                                existing_resource_file_s3_links):
        if files:
            new_resource_file_s3_links = self._upload_files(organization_ids, files, instance)
            all_resource_file_s3_links = self._concatenate_unique_lists(existing_resource_file_s3_links,
                                                                        new_resource_file_s3_links,
                                                                        resource_file_s3_links)
            instance.resource_file_s3_links = all_resource_file_s3_links
        else:
            all_resource_file_s3_links = self._concatenate_unique_lists(existing_resource_file_s3_links,
                                                                        resource_file_s3_links)
            instance.resource_file_s3_links = all_resource_file_s3_links
        return all_resource_file_s3_links

    def _update_task_history(self, instance, changes_data):
        task_history = instance.task_history
        if task_history is None:
            TaskHistory.objects.create(changes_data=changes_data)
        else:
            task_history.changes_data.extend(changes_data)
            task_history.save()

    def _update_task_report_users(self, instance, user_list, task_report_file):
        task = Task.objects.filter(id=instance.id).first()

        if user_list:
            task.user_list = user_list
        if task_report_file:
            # Upload the file to S3 and update the task_report_link field
            file_content = task_report_file.read()
            file_name = task_report_file.name
            root_folder_name = "task_report_files"
            task_id = instance.id
            current_year = instance.due_date
            folder_name = f"{root_folder_name}/{task_id}_{current_year}"
            content_type = task_report_file.content_type
            report_s3_file_link = upload_file_to_s3_folder(file_content, file_name, content_type,
                                                           folder_name)
            task.task_report_link = [report_s3_file_link]

        task.save()

    def _concatenate_unique_lists(self, *lists):
        combined_set = set()

        for lst in lists:
            for d in lst:
                # Convert nested dictionaries to tuples for hashing
                d_tuple = (
                    ('file_link', tuple(sorted(d['file_link'].items()))),
                    ('file_name', d['file_name'])
                )
                combined_set.add(d_tuple)

        # Convert back to list of dictionaries
        combined_list = [dict(t) for t in combined_set]

        # Reconstruct nested dictionaries for 'file_link'
        for d in combined_list:
            d['file_link'] = dict(d['file_link'])

        # Sorting the list of dictionaries to maintain the order
        combined_list = sorted(combined_list, key=lambda x: x['file_name'])

        return combined_list

    def _upload_task_resource_file(self, s3_files):
        resource_files_folder = "task_resource_files"
        self._create_folders([resource_files_folder])

        # Use list comprehension for a cleaner approach
        resource_file_s3_links = [
            {
                f"s3_file_{index + 1}": upload_file_to_s3_folder(
                    file.read(),
                    file.name,
                    file.content_type,
                    resource_files_folder
                )
            }
            for index, file in enumerate(s3_files)
        ]

        return resource_file_s3_links

    def _upload_files(self, organization_ids, files, task_data):
        resource_file_s3_links = []
        task_title = task_data.task_title.replace(" ", "_")
        resource_files_folder_name = f"Resource_Files/{task_title}_{task_data.task_uuid}"

        self._create_folders([resource_files_folder_name])
        for organization_id in organization_ids:
            organization = self._get_organization(organization_id)
            organization_folder = f"Organizations/{organization.company_name}_{organization.id}"
            organization_task_folder = f"{organization_folder}/{task_title}_{task_data.task_uuid}"
            self._create_folders([organization_folder, organization_task_folder])

            for resource_file in files:
                file_content = resource_file.read()
                resource_file_s3_link = upload_file_to_s3_folder(file_content, resource_file.name,
                                                                 resource_file.content_type, organization_task_folder)
                resource_file_s3_links.append(resource_file_s3_link)
                resource_file.seek(0)  # Reset file pointer after reading

                upload_file_to_s3_folder(file_content, resource_file.name, resource_file.content_type,
                                         resource_files_folder_name)
        return resource_file_s3_links

    def _create_folders(self, folder_names):
        for folder_name in folder_names:
            try:
                self.s3.head_object(Bucket=self.bucket_name, Key=f'{folder_name}/')
            except self.s3.exceptions.ClientError as e:
                if e.response['Error']['Code'] == '404':
                    self.s3.put_object(Bucket=self.bucket_name, Key=f'{folder_name}/')


class TaskHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskHistory
        fields = '__all__'


class DeletionReasonSerializer(serializers.Serializer):
    reason_for_deletion = serializers.CharField(required=True)

    # You can also add validation here if necessary
    def validate_reason_for_deletion(self, value):
        if not value.strip():
            raise serializers.ValidationError("Reason for deletion cannot be empty.")
        return value


class TaskWithDeletedHistorySerializer(serializers.Serializer):
    # For Task fields, we'll just get all fields dynamically
    task_uuid = serializers.CharField(source='task_uuid', required=False)
    task_title = serializers.CharField(source='task_title', required=False)
    manual_reference = serializers.CharField(source='manual_reference', required=False)
    schedule_date = serializers.DateField(source='schedule_date', required=False)
    due_date = serializers.DateField(source='due_date', required=False)
    additional_tags = serializers.CharField(source='additional_tags', required=False)
    overview = serializers.CharField(source='overview', required=False)
    answer_data = serializers.CharField(source='answer_data', required=False)
    frequency = serializers.CharField(source='frequency', required=False)
    frequency_due_date = serializers.JSONField(source='frequency_due_date', required=False)
    s3_file_links = serializers.JSONField(source='s3_file_links', required=False)
    resource_file_s3_links = serializers.JSONField(source='resource_file_s3_links', required=False)
    template_json_data = serializers.CharField(source='template_json_data', required=False)
    task_status = serializers.CharField(source='task_status', required=False)
    user_list = serializers.JSONField(source='user_list', required=False)
    task_report_link = serializers.JSONField(source='task_report_link', required=False)
    frequency_period = serializers.CharField(source='frequency_period', required=False)
    task_history = TaskHistorySerializer(source='task_history', required=False)  # Use nested serializer
    created_by = serializers.CharField(source='created_by.username', required=False)
    updated_by = serializers.CharField(source='updated_by.username', required=False)
    created_at = serializers.DateTimeField(source='created_at', required=False)
    updated_at = serializers.DateTimeField(source='updated_at', required=False)
    assigned_by = serializers.CharField(source='assigned_by', required=False)
    completed_at = serializers.DateField(source='completed_at', required=False)

    # Fields for DeletedTaskHistory objects (these will be added inside task_data for deleted tasks)
    deleted_at = serializers.DateTimeField(source='deleted_at', required=False)
    reason_for_deletion = serializers.CharField(source='reason_for_deletion', required=False)
    deleted_by = serializers.CharField(source='deleted_by.username', required=False)

    def to_representation(self, instance):
        # If instance is a Task, return all fields from Task model
        if isinstance(instance, Task):
            task_history_data = instance.task_history
            task_history_rep = []

            if task_history_data:
                for change in task_history_data.changes_data:
                    task_history_rep.append({
                        "changes": change['changes'],
                        "date_time": change['date_time'],
                    })

            return {
                'id': instance.id,
                'task_uuid': instance.task_uuid,
                'task_title': instance.task_title,
                'manual_reference': instance.manual_reference,
                'schedule_date': instance.schedule_date,
                'due_date': instance.due_date,
                'additional_tags': instance.additional_tags,
                'overview': instance.overview,
                'answer_data': instance.answer_data,
                'frequency': instance.frequency,
                'frequency_due_date': instance.frequency_due_date,
                's3_file_links': instance.s3_file_links,
                'resource_file_s3_links': instance.resource_file_s3_links,
                'template_json_data': instance.template_json_data,
                'task_status': instance.task_status,
                'user_list': instance.user_list,
                'task_report_link': instance.task_report_link,
                'frequency_period': instance.frequency_period,
                'task_history': task_history_rep,
                'created_by': instance.created_by.username if instance.created_by else None,
                'updated_by': instance.updated_by.username if instance.updated_by else None,
                'created_at': instance.created_at,
                'updated_at': instance.updated_at,
                'assigned_by': instance.assigned_by,
                'completed_at': instance.completed_at,
            }

        # If instance is a DeletedTaskHistory, modify and return task_data with added fields
        elif isinstance(instance, DeletedTaskHistory):
            task_data = instance.task_data  # This is a dictionary, as you described

            # Add the deleted task history information inside task_data
            task_data['deleted_task_id'] = instance.id
            task_data['task_history'] = instance.task_history
            task_data['reason_for_deletion'] = instance.reason_for_deletion
            task_data['deleted_at'] = instance.deleted_at
            task_data['deleted_by'] = instance.deleted_by.username if instance.deleted_by else None

            # Set the task status to "Deleted"
            task_data['task_status'] = "Deleted"

            return task_data

        return {}

    class Meta:
        fields = ['task_uuid', 'task_title', 'schedule_date', 'due_date', 'task_status', 'created_by', 'deleted_at',
                  'reason_for_deletion', 'deleted_by', 'manual_reference', 'additional_tags', 'overview', 'answer_data',
                  'frequency', 'frequency_due_date', 's3_file_links', 'resource_file_s3_links', 'template_json_data',
                  'user_list', 'task_report_link', 'frequency_period', 'task_history', 'created_at', 'updated_at',
                  'assigned_by', 'completed_at']
