from django.contrib import admin
from .models import *

admin.site.register(SecRuleLinks)
admin.site.register(RegulatoryReview)
admin.site.register(RegulatoryRule)
admin.site.register(RiskAssessmentSection)
admin.site.register(RiskAssessmentQuestion)
admin.site.register(RiskAssessmentOrgQuestionResponse)
admin.site.register(RiskAssessmentOrgAverageScore)
admin.site.register(PoliciesAndProcedures)
admin.site.register(ProcedureReview)
admin.site.register(ComplianceMeetingTopic)
admin.site.register(ComplianceMeetingQuestion)
admin.site.register(ComplianceMeeting)
admin.site.register(AnnualReport)
