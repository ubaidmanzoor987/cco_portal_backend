from ..views import *
from django.urls import path

risk_assessment_instructions_patterns = [
    path('create/', RiskAssessmentInstructionsViewSet.as_view({'post': 'create'}),
         name='risk_assessment_instructions_create'),
    path('', RiskAssessmentInstructionsViewSet.as_view({'get': 'list'}),
         name='risk_assessment_instructions_list'),
    path('<int:pk>/', RiskAssessmentInstructionsViewSet.as_view({'get': 'retrieve'}),
         name='risk_assessment_instructions_detail'),
    path('<int:pk>/update/',
         RiskAssessmentInstructionsViewSet.as_view({'patch': 'partial_update'}),
         name='risk_assessment_instructions_update'),
    path('<int:pk>/delete/', RiskAssessmentInstructionsViewSet.as_view({'delete': 'destroy'}),
         name='risk_assessment_instructions_delete'),
]

question_patterns = [
    path('create/', RiskAssessmentQuestionViewSet.as_view({'post': 'create'}), name='question_create'),
    path('', RiskAssessmentQuestionViewSet.as_view({'get': 'list'}), name='question_list'),
    path('<int:pk>/', RiskAssessmentQuestionViewSet.as_view({'get': 'retrieve'}), name='question_detail'),
    path('<int:pk>/update/', RiskAssessmentQuestionViewSet.as_view({'put': 'update', 'patch': 'partial_update'}),
         name='question_update'),
    path('<int:pk>/delete/', RiskAssessmentQuestionViewSet.as_view({'delete': 'destroy'}), name='question_delete'),
]

section_patterns = [
    path('create/', SectionWithQuestionViewSet.as_view({'post': 'create'}), name='section_create'),
    path('', RiskAssessmentSectionViewSet.as_view({'get': 'list'}), name='section_list'),
    path('<int:pk>/', RiskAssessmentSectionViewSet.as_view({'get': 'retrieve'}), name='section_detail'),
    path('<int:pk>/update/', RiskAssessmentSectionViewSet.as_view({'put': 'update', 'patch': 'partial_update'}),
         name='section_update'),
    path('<int:pk>/delete/', RiskAssessmentSectionViewSet.as_view({'delete': 'destroy'}), name='section_delete'),
]

response_patterns = [
    path('create/', RiskAssessmentOrgQuestionResponseViewSet.as_view({'post': 'create'}), name='response_create'),
    path('', RiskAssessmentOrgQuestionResponseViewSet.as_view({'get': 'list'}), name='response_list'),
    path('<int:pk>/', RiskAssessmentOrgQuestionResponseViewSet.as_view({'get': 'retrieve'}), name='response_detail'),
    path('update/', RiskAssessmentOrgQuestionResponsePartialUpdateView.as_view({'patch': 'partial_update'}),
         name='response_update'),
    path('reset-section/<int:section_id>/',
         RiskAssessmentOrgQuestionResponseViewSet.as_view({'get': 'reset_section'}),
         name='reset_section'),
]
