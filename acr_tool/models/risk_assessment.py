from django.db import models
from accounts.models import CustomUser
from organization.models import Organization
from django.core.exceptions import ValidationError


class RiskAssessmentSection(models.Model):
    section = models.CharField(max_length=200, unique=True)
    section_order = models.PositiveSmallIntegerField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name='created_rasections')
    created_at = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.section

    class Meta:
        verbose_name = "Risk Assessment Section"
        verbose_name_plural = "Risk Assessment Sections"
        constraints = [
            models.UniqueConstraint(fields=['section'], name='unique_section')
        ]


class RiskAssessmentQuestion(models.Model):
    section = models.ForeignKey(RiskAssessmentSection, on_delete=models.CASCADE, related_name='questions')
    question = models.TextField()
    yes_score = models.PositiveSmallIntegerField()
    no_score = models.PositiveSmallIntegerField()
    question_order = models.PositiveSmallIntegerField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name='created_raquestions')
    created_at = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.question

    class Meta:
        verbose_name = "Risk Assessment Question"
        verbose_name_plural = "Risk Assessment Questions"
        constraints = [
            models.UniqueConstraint(fields=['section', 'question'], name='unique_section_question')
        ]

    def clean(self):
        if not (0 <= self.yes_score <= 10):
            raise ValidationError({'yes_score': 'yes_score must be between 0 and 10.'})
        if not (0 <= self.no_score <= 10):
            raise ValidationError({'no_score': 'no_score must be between 0 and 10.'})


class RiskAssessmentOrgQuestionResponse(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='responses', null=True,
                                     blank=True)
    section = models.ForeignKey(RiskAssessmentSection, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(RiskAssessmentQuestion, on_delete=models.CASCADE, related_name='responses')
    response = models.BooleanField(blank=True, null=True)  # defalut response = None
    response_score = models.IntegerField()  # defalut score = -1
    note = models.TextField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name='created_raqresponses')
    created_at = models.DateField(auto_now_add=True)

    def __str__(self):
        return f'{self.organization} - {self.question}'

    class Meta:
        verbose_name = "Organization Question Response"
        verbose_name_plural = "Organization Question Responses"


class RiskAssessmentOrgAverageScore(models.Model):
    section = models.ForeignKey(RiskAssessmentSection, on_delete=models.CASCADE, related_name='average_scores')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='average_scores', null=True,
                                     blank=True)
    average_score = models.FloatField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name='created_raoscores')
    created_at = models.DateField(auto_now_add=True)

    def __str__(self):
        return f'{self.organization} - {self.section}'

    class Meta:
        verbose_name = "Organization Average Score"
        verbose_name_plural = "Organization Average Scores"


class RiskAssessmentInstructions(models.Model):
    instructions = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
