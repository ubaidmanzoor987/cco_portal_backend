from django.urls import path
from ..views import *

compliance_meeting_instructions_patterns = [
    path('create/', ComplianceMeetingInstructionsViewSet.as_view({'post': 'create'}),
         name='compliance_meeting_instructions_create'),
    path('', ComplianceMeetingInstructionsViewSet.as_view({'get': 'list'}),
         name='compliance_meeting_instructions_list'),
    path('<int:pk>/', ComplianceMeetingInstructionsViewSet.as_view({'get': 'retrieve'}),
         name='compliance_meeting_instructions_detail'),
    path('<int:pk>/update/',
         ComplianceMeetingInstructionsViewSet.as_view({'patch': 'partial_update'}),
         name='compliance_meeting_instructions_update'),
    path('<int:pk>/delete/', ComplianceMeetingInstructionsViewSet.as_view({'delete': 'destroy'}),
         name='compliance_meeting_instructions_delete'),
]

compliance_meeting_patterns = [
    path('', TopicViewSet.as_view({'get': 'list'}), name='compliance_meeting_list'),
    path('<int:pk>/', TopicViewSet.as_view({'get': 'retrieve'}), name='compliance_meeting_detail'),
    path('create/', TopicViewSet.as_view({'post': 'create'}), name='compliance_meeting_create'),
    path('<int:pk>/update/', TopicViewSet.as_view({'patch': 'update'}), name='compliance_meeting_update'),
    path('<int:pk>/delete/', TopicViewSet.as_view({'delete': 'destroy'}), name='compliance_meeting_delete'),
    path('create_topic/', ComplianceMeetingTopicViewSet.as_view({'post': 'create'}),
         name='compliance_meeting_only_create'),
]

compliance_meeting_response_patterns = [
    path('current_year/', ComplianceMeetingCurrentYearViewSet.as_view({'get': 'get_current_year_compliance_meeting'}),
         name='compliance_meeting_current_year'),
    path('create/', ComplianceMeetingViewSet.as_view({'post': 'create'}), name='compliance_meeting_response_create'),
    path('<int:pk>/update/', ComplianceMeetingViewSet.as_view({'patch': 'update'}),
         name='compliance_meeting_response_update'),
    path('sample_payload/', ComplianceMeetingViewSet.as_view({'get': 'sample_payload'}),
         name='compliance_meeting_sample_payload'),
]
