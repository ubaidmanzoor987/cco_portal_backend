from rest_framework import serializers
from fiduciary.models import *

class FiduciaryFileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        return value


class ReportDashboardSerializer(serializers.ModelSerializer):
    account = serializers.CharField(source="id") 
    report_file = serializers.CharField(source="s3_file_link")
    last_name = serializers.CharField(source="client_details.last_name")
    first_name = serializers.CharField(source="client_details.first_name")
    client_email = serializers.CharField(source="client_details.client_email")
    advisor_last_name = serializers.SerializerMethodField()

    class Meta:
        model = FiduciaryReport
        fields = ['account', 'report_file', 'last_name', 'first_name', 'client_email', 'advisor_last_name']

    def get_advisor_last_name(self, obj):
        # Ensure that client_details exists before trying to access its properties
        if hasattr(obj, 'client_details') and obj.client_details is not None:
            if obj.client_details.advisor_full_name:
                return obj.client_details.advisor_full_name.split()[-1]  # Return the last name
        return ""  # Return empty string if not available


class FiduciaryReportFileUpdateSerializer(serializers.ModelSerializer):
    
    # Nested serializer for client details
    first_name = serializers.CharField(source='client_details.first_name', required=False)
    last_name = serializers.CharField(source='client_details.last_name', required=False)

    # For previous plan and recommended plan types
    previous_plan_type = serializers.CharField(required=False, allow_blank=True)
    recommended_plan_type = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = FiduciaryReport
        fields = [
            'disclosures_delivered',
            'alternative_plans_presented',
            'fee_services_analysis',
            'best_interest_recommendation',
            'notes',
            'first_name',
            'last_name',
            'previous_plan_type',
            'recommended_plan_type'
        ]

    def update(self, instance, validated_data):
        # Update FiduciaryReport fields
        fiduciary_report_data = {
            key: value for key, value in validated_data.items()
            if key in ['disclosures_delivered', 'alternative_plans_presented', 'fee_services_analysis', 'best_interest_recommendation', 'notes']
        }
        FiduciaryReport.objects.filter(id=instance.id).update(**fiduciary_report_data)

        # Update client details (first_name, last_name)
        if 'client_details' in validated_data:
            client_details_data = validated_data.pop('client_details')
            client_details = instance.client_details
            client_details.first_name = client_details_data.get('first_name', client_details.first_name)
            client_details.last_name = client_details_data.get('last_name', client_details.last_name)
            client_details.save()

        # Update or create previous plan type
        previous_plan_type = validated_data.get('previous_plan_type')
        if previous_plan_type:
            previous_plan_service = instance.plan_services.filter(current_plan=True).first()
            if previous_plan_service:
                previous_plan_service.general_plan_service.service_name = previous_plan_type
                previous_plan_service.general_plan_service.save()
            else:
                new_service = GeneralReportPlanService.objects.create(service_name=previous_plan_type)
                ReportPlanServices.objects.create(
                    fiduciaryreport=instance,
                    general_plan_service=new_service,
                    current_plan=True
                )

        # Update or create recommended plan type
        recommended_plan_type = validated_data.get('recommended_plan_type')
        if recommended_plan_type:
            recommended_plan_service = instance.plan_services.filter(recommended_ira=True).first()
            if recommended_plan_service:
                recommended_plan_service.general_plan_service.service_name = recommended_plan_type
                recommended_plan_service.general_plan_service.save()
            else:
                new_service = GeneralReportPlanService.objects.create(service_name=recommended_plan_type)
                ReportPlanServices.objects.create(
                    fiduciaryreport=instance,
                    general_plan_service=new_service,
                    recommended_ira=True
                )

        return instance

    def to_representation(self, instance):
        """
        Custom representation to ensure previous_plan_type and recommended_plan_type
        are returned correctly in the response.
        """
        representation = super().to_representation(instance)

        # Fetch the previous plan service and recommended plan service
        previous_plan_service = instance.plan_services.filter(current_plan=True).first()
        recommended_plan_service = instance.plan_services.filter(recommended_ira=True).first()

        # Get the service_name from the related GeneralReportPlanService, if it exists
        representation['previous_plan_type'] = previous_plan_service.general_plan_service.service_name if previous_plan_service and previous_plan_service.general_plan_service else ""
        representation['recommended_plan_type'] = recommended_plan_service.general_plan_service.service_name if recommended_plan_service and recommended_plan_service.general_plan_service else ""

        return representation





class UpdateReportFileDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FiduciaryReport
        fields = ['cover_page', 'introduction_page', 'disclosures']