from django.urls import path, include
from rest_framework.routers import DefaultRouter
from fiduciary.views import *
from .views import *

# Define router for viewsets
router = DefaultRouter()
router.register(r'retrospective/questions', RetrospectiveKeyReviewQuestionViewSet, basename='key-review-questions')
router.register(r'client-requirements', ClientRequirementsViewSet, basename='client-requirements')
router.register(r'plan-service', PlanServiceViewSet, basename='plan-service')

urlpatterns = [
 
    # Include the router URLs
    path('fiduciary/report/', include(router.urls)),

    # Fiduciary report related endpoints (CRUD and file operations)
    path('fiduciary/report/create/', FiduciaryReportViewSet.as_view({"post": "create"}), name="fiduciary_report_create"),
    path('fiduciary/reports/draft/', FiduciaryReportViewSet.as_view({"get": "get_user_drafts"}), name="fiduciary_report_drafts"),
    path('fiduciary/report/update/<int:pk>/', FiduciaryReportViewSet.as_view({"put": "update", "patch": "partial_update"}), name="fiduciary_report_update"),
    path('fiduciary/report/<int:pk>/retrieve/', FiduciaryReportViewSet.as_view({"get": "retrieve"}), name="fiduciary_report_retrieve"),
    path('fiduciary/report/<int:pk>/delete/', FiduciaryReportViewSet.as_view({"delete": "destroy"}), name="fiduciary_report_destroy"),
    path('fiduciary/report/clients/bulk-upload/', BulkClientUploadViewSet.as_view({"post": "create"}), name="clients_bulk_upload"),
    path('fiduciary/report/clients/documents/upload/', ReportResourcesReviewedViewSet.as_view({"post": "upload_documents"}), name="clients_upload_documents"),

    # For retrieving plan services and client requirements by report ID
    path('fiduciary/report/<int:report_id>/plan-services/', PlanServiceViewSet.as_view({'get': 'get_plan_services_by_report'}), name='get_plan_services_by_report'),
    path('fiduciary/report/<int:report_id>/client-requirements/', ClientRequirementsViewSet.as_view({'get': 'get_client_requirements_by_report'}), name='get_client_requirements_by_report'),

    # File management endpoints
    path('fiduciary/report/file/<int:pk>/update/', FiduciaryReportFileViewSet.as_view({"put": "update_report_file_details"}), name="update_report_file_details"),
    path('fiduciary/report/file/<int:pk>/details/', FiduciaryReportFileViewSet.as_view({"get": "get_report_file_details"}), name="get_report_file_details"),
    path('fiduciary/report/<int:report_id>/file/upload/', FiduciaryFileUploadViewSet.as_view({'post': 'create'}), name='file_upload'),
    path('fiduciary/report/<int:report_id>/file/download/word/', PDFToWordConversionViewSet.as_view({'get': 'convert_to_word'}), name='convert_to_word'),
    
    
    # Dashboard and Report retrieval
    path('fiduciary/report/dashboard/', ReportDashboardViewSet.as_view({'get': 'list'}), name='fiduciary_report_dashboard'),
    

    # Retrospective review endpoints
    path('fiduciary/retrospective/<int:year>/review/', RetrospectiveReviewViewSet.as_view({'get': 'get_reviews_by_year'}), name="retrospective_review_by_year"),
    path('fiduciary/retrospective/report/<int:pk>/update/', FiduciaryReportReviewUpdateView.as_view({'put': 'update_report_review'}), name='update_report_review'),
    path('fiduciary/retrospective/review/questions/', RetrospectiveKeyReviewAnswerViewSet.as_view({'put': 'update_answers_and_notes'}), name='fiduciary_retrospective_update_answers_and_notes'),
    
 
    # Signup and Invitation endpoints
    path('fiduciary/signup/invitation/',  SignUpInvitationViewSet.as_view({'post': 'create'}), name='fiduciary_signup_invitation'),
    path('fiduciary/signup/', SignUpViewSet.as_view({'post': 'post'}), name='fiduciary_signup'),
]
