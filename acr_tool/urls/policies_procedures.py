from ..views import *
from django.urls import path

policies_procedures_instructions_patterns = [
    path('create/', PoliciesAndProceduresInstructionsViewSet.as_view({'post': 'create'}),
         name='policies_procedures_instructions_create'),
    path('', PoliciesAndProceduresInstructionsViewSet.as_view({'get': 'list'}),
         name='policies_procedures_instructions_list'),
    path('<int:pk>/', PoliciesAndProceduresInstructionsViewSet.as_view({'get': 'retrieve'}),
         name='policies_procedures_instructions_detail'),
    path('<int:pk>/update/',
         PoliciesAndProceduresInstructionsViewSet.as_view({'patch': 'partial_update'}),
         name='policies_procedures_instructions_update'),
    path('<int:pk>/delete/', PoliciesAndProceduresInstructionsViewSet.as_view({'delete': 'destroy'}),
         name='policies_procedures_instructions_delete'),
]

policies_procedures_patterns = [
    path('create/', PoliciesAndProceduresViewSet.as_view({'post': 'create'}), name='policies_procedures_create'),
    path('', PoliciesAndProceduresViewSet.as_view({'get': 'list'}), name='policies_procedures_list'),
    path('<int:pk>/', PoliciesAndProceduresViewSet.as_view({'get': 'retrieve'}), name='policies_procedures_detail'),
    path('update/<int:pk>/', PoliciesAndProceduresViewSet.as_view({'patch': 'partial_update'}),
         name='policies_procedures_update'),
    path('delete/<int:pk>/', PoliciesAndProceduresViewSet.as_view({'delete': 'destroy'}),
         name='policies_procedures_delete'),
    path('current-year/', PoliciesAndProceduresViewSet.as_view({'get': 'current_year'}),
         name='policies_procedures_current_year'),
    path('<int:pk>/delete-file/', PoliciesAndProceduresFileDeleteView.as_view(),
         name='policies_procedures_delete_file')
]
