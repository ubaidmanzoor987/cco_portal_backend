from django.db import models
from task.models import Task
from accounts.models import CustomUser
from organization.models import Organization


class ProcedureReview(models.Model):
    task = models.ManyToManyField(Task, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)
    compliance_calender_report_link = models.JSONField(default=list, null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateField(auto_now_add=True)


class ProcedureReviewInstructions(models.Model):
    instructions = models.TextField(blank=True, null=True)
    overview = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
