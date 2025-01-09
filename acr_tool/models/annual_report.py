from django.db import models
from accounts.models import CustomUser
from organization.models import Organization


class AnnualReportInstructions(models.Model):
    instructions = models.TextField(blank=True, null=True)
    background = models.TextField(blank=True, null=True)
    overview_crp = models.TextField(blank=True, null=True)
    regulatory_developments = models.TextField(blank=True, null=True)
    work_completed = models.TextField(blank=True, null=True)
    test_conducted = models.TextField(blank=True, null=True)
    conclusion = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AnnualReport(models.Model):
    cover_page = models.TextField(blank=True, null=True)
    introduction_page = models.TextField(blank=True, null=True)
    background_firm_narrative = models.TextField(blank=True, null=True)
    overview_compliance_review_process = models.TextField(blank=True, null=True)
    test_recommendation_next_year = models.TextField(blank=True, null=True)
    conclusion = models.TextField(blank=True, null=True)
    blank_page = models.JSONField(default=list, null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateField(auto_now_add=True)

    def __str__(self):
        year = self.created_at.year
        return f"Annual Report for {year}"
