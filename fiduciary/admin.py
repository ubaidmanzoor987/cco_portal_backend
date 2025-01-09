from django.contrib import admin
from .models import (
    FiduciaryReport, ReportClientDetails, ReportResourcesReviewed, ReportGeneralClientRequirement,
    ReportClientRequirements, GeneralReportPlanService, ReportPlanServices, ReportCostComparison,
    ReportNewPlanRecommendation, RetrospectiveKeyReviewQuestion, RetrospectiveKeyReviewAnswer, SignUpInvitation
)


# Define custom admin classes for each model
@admin.register(FiduciaryReport)
class FiduciaryReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'is_draft', 'created_at', 'updated_at']
    search_fields = ['user__username', 'user__email']
    list_filter = ['is_draft', 'created_at', 'updated_at']


@admin.register(ReportClientDetails)
class ReportClientDetailsAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'client_email', 'advisor_full_name', 'date_prepared']
    search_fields = ['first_name', 'last_name', 'client_email', 'advisor_full_name']
    list_filter = ['type_of_client', 'client_risk_tolerance', 'investment_objective']


@admin.register(ReportResourcesReviewed)
class ReportResourcesReviewedAdmin(admin.ModelAdmin):
    list_display = ['fiduciaryreport', 'plan_fee_data', 'form_5500', 'benchmark_data']
    list_filter = ['plan_fee_data', 'form_5500', 'benchmark_data', 'quarterly_account_statements']
    search_fields = ['fiduciaryreport__id']


@admin.register(ReportGeneralClientRequirement)
class ReportGeneralClientRequirementAdmin(admin.ModelAdmin):
    list_display = ['requirement_text']
    search_fields = ['requirement_text']


@admin.register(ReportClientRequirements)
class ReportClientRequirementsAdmin(admin.ModelAdmin):
    list_display = ['fiduciaryreport', 'status', 'notes']
    list_filter = ['status']
    search_fields = ['fiduciaryreport__id', 'status']


@admin.register(GeneralReportPlanService)
class GeneralReportPlanServiceAdmin(admin.ModelAdmin):
    list_display = ['service_name']
    search_fields = ['service_name']


@admin.register(ReportPlanServices)
class ReportPlanServicesAdmin(admin.ModelAdmin):
    list_display = ['fiduciaryreport', 'general_plan_service', 'current_plan', 'recommended_ira']
    list_filter = ['current_plan', 'recommended_ira']
    search_fields = ['general_plan_service__service_name', 'fiduciaryreport__id']


@admin.register(ReportCostComparison)
class ReportCostComparisonAdmin(admin.ModelAdmin):
    list_display = ['fiduciaryreport', 'current_plan_type', 'recommended_plan_type', 'current_total_cost', 'recommended_total_cost']
    search_fields = ['fiduciaryreport__id', 'current_plan_type', 'recommended_plan_type']
    list_filter = ['current_plan_type', 'recommended_plan_type']


@admin.register(ReportNewPlanRecommendation)
class ReportNewPlanRecommendationAdmin(admin.ModelAdmin):
    list_display = ['fiduciaryreport', 'proposed_ira_name', 'peer1_ira_name']
    search_fields = ['proposed_ira_name', 'peer1_ira_name', 'fiduciaryreport__id']


@admin.register(RetrospectiveKeyReviewQuestion)
class RetrospectiveKeyReviewQuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'is_required']
    search_fields = ['question_text']
    list_filter = ['is_required']


@admin.register(RetrospectiveKeyReviewAnswer)
class RetrospectiveKeyReviewAnswerAdmin(admin.ModelAdmin):
    list_display = ['question', 'answer', 'year_of_report']
    list_filter = ['year_of_report', 'answer']
    search_fields = ['question__question_text', 'year_of_report']


@admin.register(SignUpInvitation)
class SignUpInvitationAdmin(admin.ModelAdmin):
    list_display = ['email', 'is_used', 'expiration_date']
    list_filter = ['is_used', 'expiration_date']
    search_fields = ['email']


# Register the models in the admin interface
# admin.site.register(FiduciaryReport, FiduciaryReportAdmin)
# admin.site.register(ReportClientDetails, ReportClientDetailsAdmin)
# admin.site.register(ReportResourcesReviewed, ReportResourcesReviewedAdmin)
# admin.site.register(ReportGeneralClientRequirement, ReportGeneralClientRequirementAdmin)
# admin.site.register(ReportClientRequirements, ReportClientRequirementsAdmin)
# admin.site.register(GeneralReportPlanService, GeneralReportPlanServiceAdmin)
# admin.site.register(ReportPlanServices, ReportPlanServicesAdmin)
# admin.site.register(ReportCostComparison, ReportCostComparisonAdmin)
# admin.site.register(ReportNewPlanRecommendation, ReportNewPlanRecommendationAdmin)
# admin.site.register(RetrospectiveKeyReviewQuestion, RetrospectiveKeyReviewQuestionAdmin)
# admin.site.register(RetrospectiveKeyReviewAnswer, RetrospectiveKeyReviewAnswerAdmin)
# admin.site.register(SignUpInvitation, SignUpInvitationAdmin)
