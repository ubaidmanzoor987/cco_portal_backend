from django.db import models
from accounts.models import CustomUser
from organization.models import Organization
from django.contrib.postgres.fields import ArrayField


class SecRuleLinks(models.Model):
    FINAL_RULES = 'Final Rules'
    ENFORCEMENT_ACTIONS = 'Enforcement Actions'
    RISK_ALERTS = 'Risk Alerts'
    PRESS_RELEASES = 'Press Releases'

    SECTION_CHOICES = [
        (FINAL_RULES, 'Final Rules'),
        (ENFORCEMENT_ACTIONS, 'Enforcement Actions'),
        (RISK_ALERTS, 'Risk Alerts'),
        (PRESS_RELEASES, 'Press Releases'),
    ]
    rule_name = models.CharField(max_length=20, choices=SECTION_CHOICES)
    rule_links = ArrayField(models.URLField(max_length=200, blank=True), default=list, blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.rule_name


class RegulatoryReview(models.Model):
    title = models.CharField(max_length=200, blank=True, null=True)
    overview = models.TextField(blank=True, null=True)
    issue_date = models.DateField(blank=True, null=True)
    section = models.CharField(max_length=20, choices=SecRuleLinks.SECTION_CHOICES)
    attached_link = models.URLField(max_length=200, blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Title {self.title}: Section {self.section}"


class RegulatoryRule(models.Model):
    regulatory_review = models.ForeignKey(RegulatoryReview, on_delete=models.CASCADE)
    rule_text = models.TextField(blank=True, null=True)
    rule_order = models.IntegerField()
    created_at = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.rule_order}: Text {self.rule_text}: Regulatory_Review {self.regulatory_review}"


class RegulatoryReviewInstructions(models.Model):
    instructions = models.TextField(blank=True, null=True)
    example = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
