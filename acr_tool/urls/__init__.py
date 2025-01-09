from django.urls import path, include
from .annual_report import *
from .risk_assessment import *
from .procedure_review import *
from .aws_file_uploader import *
from .regulatory_reviews import *
from .compliance_meeting import *
from .policies_procedures import *

urlpatterns = [
    path('sec_rule_links/', include((sec_rule_links_patterns, 'sec_rule_links'))),
    path('regulatory_reviews/', include((regulatory_review_patterns, 'regulatory_reviews'))),
    path('regulatory_reviews_instructions/',
         include((regulatory_review_instructions_patterns, 'regulatory_review_instructions'))),
    path('risk_assessment_instructions/',
         include((risk_assessment_instructions_patterns, 'risk_assessment_instructions'))),
    path('risk_assessment_sections/', include((section_patterns, 'sections'))),
    path('risk_assessment_questions/', include((question_patterns, 'questions'))),
    path('risk_assessment_responses/', include((response_patterns, 'responses'))),
    path('policies_procedures_instructions/',
         include((policies_procedures_instructions_patterns, 'policies_procedures_instructions'))),
    path('policies_procedures/', include((policies_procedures_patterns, 'policies_procedures'))),
    path('procedure_review_instructions/',
         include((procedure_review_instructions_patterns, 'procedure_review_instructions'))),
    path('procedure_reviews/', include((procedure_review_patterns, 'procedure_reviews'))),
    path('compliance_meeting_instructions/',
         include((compliance_meeting_instructions_patterns, 'compliance_meeting_instructions'))),
    path('compliance_meeting/', include((compliance_meeting_patterns, 'compliance_meeting'))),
    path('compliance_meeting_response/', include((compliance_meeting_response_patterns, 'compliance_response'))),
    path('annual_report/', include((annual_report_patterns, 'annual_report'))),
    path('annual_report_instructions/', include((annual_report_instructions_patterns, 'annual_report_instructions'))),
    path('acr_instructions/', include((acr_instructions_patterns, 'acr_instructions'))),
    path('aws_resource_file/', include((aws_resource_file_patterns, 'aws_resource_file'))),
]
