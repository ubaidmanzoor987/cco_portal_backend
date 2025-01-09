import uuid
from django.db import models

from accounts.models import CustomUser
from organization.models import Organization


class TaskHistory(models.Model):
    changes_data = models.JSONField(default=list)


class DeletedTaskHistory(models.Model):
    task_data = models.JSONField()  # Store all fields of the deleted Task as JSON
    task_history = models.JSONField()  # Store the task's TaskHistory data as JSON
    reason_for_deletion = models.TextField(blank=True, null=True)
    deleted_at = models.DateTimeField(auto_now_add=True)  # Record when the task was deleted
    deleted_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="deleted_tasks"
    )  # Track the user who deleted the task
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, blank=True, null=True
    )  # organization that the task belongs to

    def __str__(self):
        return f"Deleted Task {self.task_data.get('task_title', '')}"


class Task(models.Model):
    FREQUENCY_MONTHLY = 'Monthly'
    FREQUENCY_QUARTERLY = 'Quarterly'
    FREQUENCY_YEARLY = 'Yearly'
    FREQUENCY_TWICE_A_YEAR = 'Twice a Year'

    FREQUENCY_CHOICES = [
        (FREQUENCY_MONTHLY, 'Monthly'),
        (FREQUENCY_QUARTERLY, 'Quarterly'),
        (FREQUENCY_YEARLY, 'Yearly'),
        (FREQUENCY_TWICE_A_YEAR, 'Twice a Year'),
    ]

    STATUS_COMPLETED = 'Completed'
    STATUS_UPCOMING = 'Upcoming'
    STATUS_OVERDUE = 'Overdue'
    STATUS_PENDING = 'Pending'
    STATUS_IN_PROGRESS = 'In Progress'

    STATUS_CHOICES = [
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_UPCOMING, 'Upcoming'),
        (STATUS_OVERDUE, 'Overdue'),
        (STATUS_PENDING, 'Pending'),
        (STATUS_IN_PROGRESS, 'In Progress'),
    ]

    QUARTERS = [
        ('Q1', 'First Quarter'),
        ('Q2', 'Second Quarter'),
        ('Q3', 'Third Quarter'),
        ('Q4', 'Fourth Quarter'),
    ]

    HALF_YEARS = [
        ('first_half_year', 'First Half of the Year'),
        ('second_half_year', 'Second Half of the Year'),
    ]

    ASSIGNED_BY_ADMIN = 'admin'
    ASSIGNED_BY_CCO = 'cco'

    ASSIGNED_BY_CHOICES = [
        (ASSIGNED_BY_ADMIN, 'Admin'),
        (ASSIGNED_BY_CCO, 'CCO'),
    ]

    task_uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    task_title = models.CharField(max_length=200)
    manual_reference = models.CharField(max_length=200, blank=True, null=True)
    schedule_date = models.DateField()
    due_date = models.DateField(blank=True, null=True)
    additional_tags = models.TextField(blank=True, null=True)
    overview = models.TextField(blank=True, null=True)
    answer_data = models.TextField(blank=True, null=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default=FREQUENCY_YEARLY)
    frequency_due_date = models.JSONField(default=list, blank=True, null=True)
    s3_file_links = models.JSONField(default=list, blank=True, null=True)
    resource_file_s3_links = models.JSONField(default=list, blank=True, null=True)
    template_json_data = models.TextField(blank=True, null=True)
    task_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_UPCOMING)
    user_list = models.JSONField(default=list, blank=True, null=True)
    task_report_link = models.JSONField(default=list, null=True, blank=True)
    frequency_period = models.CharField(max_length=20, blank=True, null=True)
    task_history = models.ForeignKey(TaskHistory, on_delete=models.SET_NULL, null=True, blank=True)

    created_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, blank=True, null=True, related_name="created_tasks"
    )
    updated_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, blank=True, null=True, related_name="updated_tasks"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_by = models.CharField(
        max_length=10,
        choices=ASSIGNED_BY_CHOICES,
        blank=True,
        null=True
    )
    completed_at = models.DateField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.frequency == self.FREQUENCY_QUARTERLY:
            if self.frequency_period not in dict(self.QUARTERS):
                raise ValueError("Invalid frequency period for quarterly frequency. Choose from Q1, Q2, Q3, or Q4.")
        elif self.frequency == self.FREQUENCY_MONTHLY:
            if self.frequency_period != "month":
                raise ValueError("Invalid frequency period for monthly frequency. The value should be 'month'.")
        elif self.frequency == self.FREQUENCY_TWICE_A_YEAR:
            if self.frequency_period not in dict(self.HALF_YEARS):
                raise ValueError(
                    "Invalid frequency period for twice a year frequency. Choose from 'first_half_year' or 'second_half_year'.")
        elif self.frequency == self.FREQUENCY_YEARLY:
            if self.frequency_period != "year":
                raise ValueError("Invalid frequency period for yearly frequency. The value should be 'year'.")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.task_title


class OrganizationTask(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)


class OrganizationUserTask(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True)
    organization_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
