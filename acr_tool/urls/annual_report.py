from django.urls import path
from ..views import *

annual_report_patterns = [
    path('', AnnualReportViewSet.as_view({'get': 'list'}), name='annual_report_list'),
    path('<int:pk>/', AnnualReportViewSet.as_view({'get': 'retrieve'}), name='annual_report_detail'),
    path('<int:pk>/update/', AnnualReportViewSet.as_view({'patch': 'partial_update'}), name='annual_report_update'),
    path('convert_pdf_to_word/', ConvertPDFToWordViewSet.as_view({'post': 'create'}), name='convert_pdf_to_word'),
]

annual_report_instructions_patterns = [
    path('create/', AnnualReportInstructionsViewSet.as_view({'post': 'create'}),
         name='annual_report_instructions_create'),
    path('', AnnualReportInstructionsViewSet.as_view({'get': 'list'}),
         name='annual_report_instructions_list'),
    path('<int:pk>/', AnnualReportInstructionsViewSet.as_view({'get': 'retrieve'}),
         name='annual_report_instructions_detail'),
    path('<int:pk>/update/',
         AnnualReportInstructionsViewSet.as_view({'patch': 'partial_update'}),
         name='annual_report_instructions_update'),
    path('<int:pk>/delete/', AnnualReportInstructionsViewSet.as_view({'delete': 'destroy'}),
         name='annual_report_instructions_delete'),
]

acr_instructions_patterns = [
    path('', ACRInstructionsViewSet.as_view({'get': 'list'}), name='instructions_list'),
]
