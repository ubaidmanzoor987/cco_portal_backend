from django.db import models
from accounts.models import CustomUser
from organization.models import Organization


class ComplianceMeetingInstructions(models.Model):
    instructions = models.TextField(blank=True, null=True)
    overview = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ComplianceMeetingTopic(models.Model):
    topic = models.CharField(max_length=255, unique=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.topic


class ComplianceMeetingQuestion(models.Model):
    topic = models.ForeignKey(ComplianceMeetingTopic, related_name='questions', on_delete=models.CASCADE)
    content = models.TextField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.content


class ComplianceMeetingTopicDetail(models.Model):
    meeting = models.ForeignKey('ComplianceMeeting', related_name='topic_details', on_delete=models.CASCADE)
    topic = models.ForeignKey(ComplianceMeetingTopic, related_name='meeting_details', on_delete=models.CASCADE)
    custom_questions = models.JSONField(default=list, null=True, blank=True)
    comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Meeting {self.meeting.id} - Topic {self.topic.topic}"


class ComplianceMeeting(models.Model):
    topics = models.ManyToManyField(ComplianceMeetingTopic, through='ComplianceMeetingTopicDetail',
                                    related_name='compliance_meetings', blank=True)
    sample_questions = models.ManyToManyField(ComplianceMeetingQuestion, related_name='compliance_meetings', blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Compliance Meeting {self.id}"
