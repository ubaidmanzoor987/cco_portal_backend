from django.urls import path
from ..views.procedure_review import *

procedure_review_instructions_patterns = [
    path('create/', ProcedureReviewInstructionsViewSet.as_view({'post': 'create'}),
         name='procedure_review_instructions_create'),
    path('', ProcedureReviewInstructionsViewSet.as_view({'get': 'list'}),
         name='procedure_review_instructions_list'),
    path('<int:pk>/', ProcedureReviewInstructionsViewSet.as_view({'get': 'retrieve'}),
         name='procedure_review_instructions_detail'),
    path('<int:pk>/update/',
         ProcedureReviewInstructionsViewSet.as_view({'patch': 'partial_update'}),
         name='procedure_review_instructions_update'),
    path('<int:pk>/delete/', ProcedureReviewInstructionsViewSet.as_view({'delete': 'destroy'}),
         name='procedure_review_instructions_delete'),
]

procedure_review_patterns = [
    path('', ProcedureReviewViewSet.as_view({'get': 'list'}), name='procedure_review_list'),
    path('<int:pk>/', ProcedureReviewViewSet.as_view({'get': 'retrieve'}), name='procedure_review_detail'),
    path('update/<int:pk>/', ProcedureReviewViewSet.as_view({'patch': 'partial_update'}),
         name='procedure_review_update'),
    path('delete/<int:pk>/', ProcedureReviewViewSet.as_view({'delete': 'destroy'}),
         name='procedure_review_delete'),
    # path('create/', ProcedureReviewViewSet.as_view({'post': 'create'}),
    #      name='procedure_review_create'),
]
