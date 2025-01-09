from django.db import models
from accounts.models import CustomUser
from organization.models import Organization


class AWSResourceFile(models.Model):
    REGULATORY_REVIEW = 'Regulatory Review'
    RISK_ASSESSMENT = 'Risk Assessment'
    POLICIES_PROCEDURES = 'Policies Procedures'
    PROCEDURE_REVIEW = 'Procedure Review'
    COMPLIANCE_MEETING = 'Compliance Meeting'
    ANNUAL_REPORT = 'Annual Report'

    ACR_CHOICES = [
        (REGULATORY_REVIEW, 'Regulatory Review'),
        (RISK_ASSESSMENT, 'Risk Assessment'),
        (POLICIES_PROCEDURES, 'Policies Procedures'),
        (PROCEDURE_REVIEW, 'Procedure Review'),
        (COMPLIANCE_MEETING, 'Compliance Meeting'),
        (ANNUAL_REPORT, 'Annual Report'),
    ]
    acr_tab = models.CharField(max_length=20, choices=ACR_CHOICES)
    resource_file_s3_link = models.JSONField(default=list, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return f"{self.acr_tab} ({self.created_at.year})"
