

# Django REST Framework
from rest_framework import serializers

# Models
from fiduciary.models import *
from .plan_service import *
from .client_requirement import *



class ReportClientDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportClientDetails
        exclude = ['fiduciaryreport', 'id']


class ReportResourcesReviewedSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportResourcesReviewed
        exclude = ['fiduciaryreport', 'id']


class ReportGeneralClientRequirementSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = ReportGeneralClientRequirement
        fields = ['id', 'requirement_text']


class ReportClientRequirementWithStatusSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(write_only=True)  
    requirement_text = serializers.CharField(source='general_requirement.requirement_text', read_only=True)

    class Meta:
        model = ReportClientRequirements
        fields = ['id', 'requirement_text', 'status']
    
 

# Serializer for the client requirements section linked to a FiduciaryReport
class ReportClientRequirementsSerializer(serializers.ModelSerializer):
    requirements = ReportClientRequirementWithStatusSerializer(many=True, required=False)  
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = ReportClientRequirements
        fields = ['requirements', 'notes']

    def create(self, validated_data):
        requirements_data = validated_data.pop('requirements', [])
        client_requirements_instance = ReportClientRequirements.objects.create(**validated_data)
        for req_data in requirements_data:
            requirement_id = req_data.pop('id')  # Changed to fetch ID from req_data
            status = req_data.get('status')  # This can be None now

            # Check if requirement_id is valid
            if requirement_id is not None:
                general_requirement = ReportGeneralClientRequirement.objects.get(id=requirement_id)
                ReportClientRequirements.objects.create(
                    fiduciaryreport=client_requirements_instance.fiduciaryreport,
                    general_requirement=general_requirement,
                    status=status  # Allow status to be None
                )

        return client_requirements_instance


class ReportCostComparisonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportCostComparison
        exclude = ['fiduciaryreport', 'id']


class ReportNewPlanRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportNewPlanRecommendation
        exclude = ['fiduciaryreport', 'id']


class GeneralPlanServiceSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = GeneralReportPlanService
        fields = ['id', 'service_name']


class ReportPlanServicesSerializer(serializers.ModelSerializer):
    general_plan_service = GeneralPlanServiceSerializer(read_only=True)
    id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ReportPlanServices
        fields = ['general_plan_service', 'id', 'current_plan', 'recommended_ira']

    def create(self, validated_data):
        id = validated_data.pop('id')
        # Fetch the GeneralPlanService instance
        general_plan_service = GeneralReportPlanService.objects.get(id=id)
        report_plan_service = ReportPlanServices.objects.create(general_plan_service=general_plan_service, **validated_data)
        return report_plan_service


# Serializer for PlanServicesSection with nested PlanServices
class PlanServicesSectionSerializer(serializers.Serializer):
    plan_services = ReportPlanServicesSerializer(many=True, required=False, default=list)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    
class FiduciaryReportSerializer(serializers.ModelSerializer):
    client_details = ReportClientDetailsSerializer(required=False, default=None)
    resources_reviewed = ReportResourcesReviewedSerializer(required=False, default=None)
    client_requirements = ReportClientRequirementsSerializer(required=False, default=None)
    plan_services_section = PlanServicesSectionSerializer(required=False, default=None)
    cost_comparison = ReportCostComparisonSerializer(required=False, default=None)
    plan_recommendations = ReportNewPlanRecommendationSerializer(required=False, default=None)
    is_draft = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = FiduciaryReport
        exclude = [
            'disclosures_delivered', 'alternative_plans_presented',
            'fee_services_analysis', 'best_interest_recommendation',
            'notes', 'user'
        ]
        extra_kwargs = {
            's3_file_link': {'read_only': True} 
        }

    def create(self, validated_data):
        user = self.context['request'].user

        client_details_data = validated_data.pop('client_details', None)
        resources_reviewed_data = validated_data.pop('resources_reviewed', None)
        client_requirements_data = validated_data.pop('client_requirements', None)
        plan_services_section_data = validated_data.pop('plan_services_section', {})
        cost_comparison_data = validated_data.pop('cost_comparison', None)
        plan_recommendations_data = validated_data.pop('plan_recommendations', None)
        is_draft = validated_data.pop('is_draft', False)

        try:
            fiduciary_report = FiduciaryReport.objects.create(user=user, is_draft=is_draft, **validated_data)

            if client_details_data:
                ReportClientDetails.objects.create(fiduciaryreport=fiduciary_report, **client_details_data)
            else:
                client_details_data = {}
                ReportClientDetails.objects.create(fiduciaryreport=fiduciary_report, **client_details_data)

            if resources_reviewed_data:
                ReportResourcesReviewed.objects.create(fiduciaryreport=fiduciary_report, **resources_reviewed_data)
            else:
                resources_reviewed_data = {}
                ReportResourcesReviewed.objects.create(fiduciaryreport=fiduciary_report, **resources_reviewed_data)

            if client_requirements_data:
                self._create_or_update_client_requirements(fiduciary_report, client_requirements_data)
            else:
                client_requirements_data = {}
                ReportClientRequirements.objects.create(fiduciaryreport=fiduciary_report, **client_requirements_data)

            if cost_comparison_data:
                ReportCostComparison.objects.create(fiduciaryreport=fiduciary_report, **cost_comparison_data)
            else:
                cost_comparison_data = {}
                ReportCostComparison.objects.create(fiduciaryreport=fiduciary_report, **cost_comparison_data)

            if plan_recommendations_data:
                ReportNewPlanRecommendation.objects.create(fiduciaryreport=fiduciary_report, **plan_recommendations_data)
            else:
                plan_recommendations_data = {}
                ReportNewPlanRecommendation.objects.create(fiduciaryreport=fiduciary_report, **plan_recommendations_data)

            if plan_services_section_data:
                self._create_or_update_plan_services(fiduciary_report, plan_services_section_data)
            # else:
                # plan_services_section_data = {}
                # ReportPlanServices.objects.create(fiduciaryreport=fiduciary_report, **plan_services_section_data)
                

            return fiduciary_report
        except Exception as e:
            raise serializers.ValidationError({
                "status": "error",
                "message": "There was an error creating the report.",
                "errors": str(e)
            })

    def _create_or_update_client_requirements(self, fiduciary_report, client_requirements_data):
        try:
            requirements_data = client_requirements_data.get('requirements', [])
            if not isinstance(requirements_data, list):
                raise serializers.ValidationError({
                    "status": "error",
                    "message": "There was an error processing client requirements.",
                    "errors": f"Expected a list for requirements_data, but got {type(requirements_data)}."
                })

            for requirement_data in requirements_data:
                requirement_id = requirement_data.get('id')
                status = requirement_data.get('status')

                if requirement_id is None:
                    raise serializers.ValidationError({
                        "status": "error",
                        "message": "There was an error processing client requirements.",
                        "errors": "Missing 'requirement_id' in requirement_data."
                    })

                try:
                    general_requirement = ReportGeneralClientRequirement.objects.get(id=requirement_id)
                except ReportGeneralClientRequirement.DoesNotExist:
                    raise serializers.ValidationError({
                        "status": "error",
                        "message": "There was an error processing client requirements.",
                        "errors": f"Requirement with ID {requirement_id} does not exist."
                    })

                ReportClientRequirements.objects.create(
                    fiduciaryreport=fiduciary_report,
                    general_requirement=general_requirement,
                    status=status,  # Allow status to be None
                    notes=client_requirements_data.get('notes', '')
                )
        except Exception as e:
            raise serializers.ValidationError({
                "status": "error",
                "message": "There was an error processing client requirements.",
                "errors": str(e)
            })

    def _create_or_update_plan_services(self, fiduciary_report, plan_services_section_data):
        try:
            plan_services_data = plan_services_section_data.get('plan_services', [])
            notes = plan_services_section_data.get('notes', '')
            for plan_service_data in plan_services_data:
                id = plan_service_data.get('id')

                try:
                    general_plan_service = GeneralReportPlanService.objects.get(id=id)
                except GeneralReportPlanService.DoesNotExist:
                    raise serializers.ValidationError({
                        "status": "error",
                        "message": "There was an error processing plan services.",
                        "errors": f"Plan Service with ID {id} does not exist."
                    })

                ReportPlanServices.objects.create(
                    fiduciaryreport=fiduciary_report,
                    general_plan_service=general_plan_service,
                    current_plan=plan_service_data.get('current_plan', False),
                    recommended_ira=plan_service_data.get('recommended_ira', False),
                    notes=notes
                )
        except Exception as e:
            raise serializers.ValidationError({
                "status": "error",
                "message": "There was an error processing plan services.",
                "errors": str(e)
            })

    
    def to_representation(self, instance):
        representation = super().to_representation(instance)

        # Include client requirements with their status and notes
        if instance.client_requirements.exists():
            requirements_data = [
                {
                    'id': req.general_requirement.id,
                    'requirement_text': req.general_requirement.requirement_text,
                    'status': req.status
                }
                for req in instance.client_requirements.all() if req.general_requirement 
            ]
            representation['client_requirements'] = {
                'requirements': requirements_data,
                'notes': instance.client_requirements.first().notes  # Get the notes from one of the related requirements
            }
        else:
            representation['client_requirements'] = {'requirements': [], 'notes': ''}

        # Handle plan services section with default values if not present
        if instance.plan_services.exists():
            plan_services_section = [
                {
                    'id': plan_service.general_plan_service.id if plan_service.general_plan_service else None,
                    'service_name': plan_service.general_plan_service.service_name if plan_service.general_plan_service else None,
                    'current_plan': plan_service.current_plan if plan_service.general_plan_service else None,
                    'recommended_ira': plan_service.recommended_ira if plan_service.general_plan_service else None
                }
            
                for plan_service in instance.plan_services.all()
            ] if instance.plan_services.exists() else []

            representation['plan_services_section'] = {
                'plan_services': plan_services_section,
                'notes': (instance.plan_services.first()).notes
            }
        else:
            representation['plan_services_section'] = {'plan_services': [], 'notes': ''}

        representation['cost_comparison'] = ReportCostComparisonSerializer(getattr(instance, 'cost_comparison', None)).data if getattr(instance, 'cost_comparison', None) else {}
        representation['plan_recommendations'] = ReportNewPlanRecommendationSerializer(getattr(instance, 'plan_recommendations', None)).data if getattr(instance, 'plan_recommendations', None) else {}

        return representation

    def update(self, instance, validated_data):
        try:
            client_details_data = validated_data.pop('client_details', None)
            resources_reviewed_data = validated_data.pop('resources_reviewed', None)
            client_requirements_data = validated_data.pop('client_requirements', None)
            plan_services_section_data = validated_data.pop('plan_services_section', {})
            cost_comparison_data = validated_data.pop('cost_comparison', None)
            plan_recommendations_data = validated_data.pop('plan_recommendations', None)
            is_draft = validated_data.pop('is_draft', instance.is_draft)

            instance.is_draft = is_draft
            instance.save()

            if client_details_data:
                ReportClientDetails.objects.update_or_create(fiduciaryreport=instance, defaults=client_details_data)
            if resources_reviewed_data:
                ReportResourcesReviewed.objects.update_or_create(fiduciaryreport=instance, defaults=resources_reviewed_data)

            if client_requirements_data:
                ReportClientRequirements.objects.filter(fiduciaryreport=instance).delete()
                self._create_or_update_client_requirements(instance, client_requirements_data)

            if cost_comparison_data:
                ReportCostComparison.objects.update_or_create(fiduciaryreport=instance, defaults=cost_comparison_data)
            if plan_recommendations_data:
                ReportNewPlanRecommendation.objects.update_or_create(fiduciaryreport=instance, defaults=plan_recommendations_data)

            if plan_services_section_data:
                ReportPlanServices.objects.filter(fiduciaryreport=instance).delete()
                self._create_or_update_plan_services(instance, plan_services_section_data)

            return instance
        except serializers.ValidationError as e:
            raise e
        except Exception as e:
            raise serializers.ValidationError({
                "status": "error",
                "message": "There was an error updating the report.",
                "errors": str(e)
            })


class ClientDataUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

class DocumentUploadSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=serializers.FileField(),  # Accepts file uploads
        allow_empty=False,  # Ensure at least one file is uploaded
        required=True
    )