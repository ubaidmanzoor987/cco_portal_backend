from ..views import *
from django.urls import path

sec_rule_links_patterns = [
    path('create/', SecRuleLinksViewSet.as_view({'post': 'create'}), name='sec_rule_links_create'),
    path('', SecRuleLinksViewSet.as_view({'get': 'list'}), name='sec_rule_links_list'),
    path('<int:pk>/', SecRuleLinksViewSet.as_view({'get': 'retrieve'}), name='sec_rule_links_detail'),
    path('<int:pk>/update/', SecRuleLinksViewSet.as_view({'put': 'update', 'patch': 'partial_update'}),
         name='sec_rule_links_update'),
    path('<int:pk>/delete/', SecRuleLinksViewSet.as_view({'delete': 'destroy'}), name='sec_rule_links_delete'),
    path('section/<str:section>/', SecRuleLinksViewSet.as_view({'get': 'get_by_section'}),
         name='sec_rule_links_section'),
]

regulatory_review_patterns = [
    path('create/', RegulatoryReviewViewSet.as_view({'post': 'create'}), name='regulatory_review_create'),
    path('', RegulatoryReviewViewSet.as_view({'get': 'list'}), name='regulatory_review_list'),
    path('<int:pk>/', RegulatoryReviewViewSet.as_view({'get': 'retrieve'}), name='regulatory_review_detail'),
    path('<int:pk>/update/', RegulatoryReviewViewSet.as_view({'put': 'update', 'patch': 'partial_update'}),
         name='regulatory_review_update'),
    path('<int:pk>/delete/', RegulatoryReviewViewSet.as_view({'delete': 'destroy'}), name='regulatory_review_delete'),
    path('year/<int:year>/', RegulatoryReviewViewSet.as_view({'get': 'get_by_year'}), name='regulatory_review_year'),
]

regulatory_review_instructions_patterns = [
    path('create/', RegulatoryReviewInstructionsViewSet.as_view({'post': 'create'}),
         name='regulatory_review_instructions_create'),
    path('', RegulatoryReviewInstructionsViewSet.as_view({'get': 'list'}),
         name='regulatory_review_instructions_list'),
    path('<int:pk>/', RegulatoryReviewInstructionsViewSet.as_view({'get': 'retrieve'}),
         name='regulatory_review_instructions_detail'),
    path('<int:pk>/update/',
         RegulatoryReviewInstructionsViewSet.as_view({'patch': 'partial_update'}),
         name='regulatory_review_instructions_update'),
    path('<int:pk>/delete/', RegulatoryReviewInstructionsViewSet.as_view({'delete': 'destroy'}),
         name='regulatory_review_instructions_delete'),
]
