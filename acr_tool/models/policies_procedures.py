from django.db import models
from accounts.models import CustomUser
from organization.models import Organization
from .regulatory_review import RegulatoryReview
from .risk_assessment import RiskAssessmentOrgQuestionResponse


class PoliciesAndProcedures(models.Model):
    risk_assessment_response = models.ForeignKey(RiskAssessmentOrgQuestionResponse, on_delete=models.CASCADE, null=True,
                                                 blank=True, related_name="policies_procedures")
    regulatory_review = models.ForeignKey(RegulatoryReview, on_delete=models.CASCADE, null=True, blank=True)
    policies_procedure_section = models.CharField(max_length=255, null=True, blank=True)
    work_flow_link = models.JSONField(default=list, null=True, blank=True)
    work_flow_text = models.TextField(blank=True, null=True)
    cco_updates_text = models.TextField(blank=True, null=True)
    policies_procedure_tab = models.CharField(max_length=255, null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_by = models.CharField(max_length=255, null=True, blank=True)
    reviewed_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Policies_Procedure_Tab:{self.policies_procedure_tab}, Organization:{self.organization}, Created_at:{self.created_at}"


class PoliciesAndProceduresInstructions(models.Model):
    instructions = models.TextField(blank=True, null=True)
    overview = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
