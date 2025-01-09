from datetime import datetime
from rest_framework import serializers

from acr_tool.models import *
from utils.s3_utils import upload_file_to_s3_folder


class PoliciesAndProceduresInstructionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PoliciesAndProceduresInstructions
        fields = ['id', 'instructions', 'overview', 'created_by', 'created_at']
        read_only_fields = ['created_by', 'created_at']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        instance.instructions = validated_data.get('instructions', instance.instructions)
        instance.overview = validated_data.get('overview', instance.overview)
        instance.save()
        return instance


class RiskAssessmentQuestionSimpleSerializer(serializers.ModelSerializer):
    question = serializers.CharField(read_only=True)  # The actual question text
    question_order = serializers.IntegerField(read_only=True)  # The order of the question (if needed)

    class Meta:
        model = RiskAssessmentQuestion
        fields = ['id', 'question', 'question_order']  # You can include other fields if necessary
        read_only_fields = ['id', 'question', 'question_order']  # These fields shouldn't be editable


class PoliciesAndProceduresSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=False)
    reviewed_date = serializers.DateField(
        input_formats=['%Y-%m-%d'],
        required=False
    )
    regulatory_review = serializers.CharField(source='regulatory_review.title', read_only=True)
    section_rule = serializers.SerializerMethodField()

    # Access the related RiskAssessmentOrgQuestionResponse fields
    risk_section_name = serializers.CharField(source='risk_assessment_response.section.section', read_only=True)
    risk_section_order = serializers.IntegerField(source='risk_assessment_response.section.section_order',
                                                  read_only=True)
    risk_question = RiskAssessmentQuestionSimpleSerializer(source='risk_assessment_response.question', read_only=True)

    class Meta:
        model = PoliciesAndProcedures
        fields = [
            'id',
            'risk_assessment_response',  # New field
            'regulatory_review',
            'section_rule',
            'policies_procedure_section',
            'work_flow_link',
            'work_flow_text',
            'cco_updates_text',
            'policies_procedure_tab',
            'organization',
            'reviewed_by',
            'reviewed_date',
            'created_by',
            'created_at',
            'file',  # This is for uploading files via the API
            'risk_section_name',
            'risk_section_order',
            'risk_question',
        ]
        read_only_fields = ['risk_assessment_response', 'risk_section_name', 'risk_section_order', 'risk_question',
                            'regulatory_review', 'work_flow_link', 'organization', 'created_by', 'created_at']

    def get_section_rule(self, obj):
        # Check if the section or regulatory review title is available to return
        regulatory_review_title = getattr(obj.regulatory_review, 'title', None)

        # Check if risk_assessment_response is not None before accessing its section
        if obj.risk_assessment_response:
            risk_section_name = getattr(obj.risk_assessment_response.section, 'section', None)
        else:
            risk_section_name = None

        # Return the appropriate value
        if risk_section_name:
            return risk_section_name
        elif regulatory_review_title:
            return regulatory_review_title
        return None

    def validate(self, data):
        # Ensure that if 'policies_procedure_tab' is 'riskAssessment',
        # 'risk_assessment_response' must not be None.
        if data.get('policies_procedure_tab') == 'riskAssessment' and not data.get('risk_assessment_response'):
            raise serializers.ValidationError(
                "risk_assessment_response is required when policies_procedure_tab is 'riskAssessment'."
            )

        # Existing validation logic
        if not self.instance:
            cco_updates_text = data.get('cco_updates_text')

            if not cco_updates_text:
                raise serializers.ValidationError(
                    {"cco_updates_text": "cco_updates_text is required when policies_procedure_tab is 'ccoUpdates'."}
                )

        # Restriction for updates
        if self.instance and any(
                field in data for field in ['risk_assessment_response', 'regulatory_review', 'work_flow_link']):
            raise serializers.ValidationError(
                "Updating risk_assessment_response, regulatory_review, and work_flow_link fields is not allowed."
            )
        return data

    def create(self, validated_data):
        file = validated_data.pop('file', None)  # Extract the file if present
        validated_data['created_by'] = self.context['request'].user
        validated_data['organization'] = self.context['request'].user.organization

        # Create the new PoliciesAndProcedures instance
        instance = PoliciesAndProcedures.objects.create(**validated_data)

        if file:
            # Handle file upload to S3 and update the instance's work_flow_link
            root_folder_name = "policies_procedures"
            current_year = datetime.utcnow().year
            section_name = "cco_updates"

            folder_name = f"{root_folder_name}/{section_name}_{current_year}"
            file_links = upload_file_to_s3_folder(file.read(), file.name, file.content_type, folder_name)

            # Update the instance with the file links
            instance.work_flow_link = [file_links]
            instance.save()

        return instance

    def update(self, instance, validated_data):
        file = validated_data.pop('file', None)

        if file:
            # Same logic as create to handle the file upload to S3
            root_folder_name = "policies_procedures"
            current_year = datetime.utcnow().year
            if instance.risk_assessment_response and instance.risk_assessment_response.section:
                section_name = instance.risk_assessment_response.section.section.lower().replace(" ", "_")
            else:
                section_name = "cco_updates"

            folder_name = f"{root_folder_name}/{section_name}_{current_year}"
            file_links = upload_file_to_s3_folder(file.read(), file.name, file.content_type, folder_name)
            instance.work_flow_link = [file_links]

        return super().update(instance, validated_data)


class PoliciesAndProceduresFileDeleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PoliciesAndProcedures
        fields = ['work_flow_link']
        read_only_fields = ['work_flow_link']

    def update(self, instance, validated_data):
        # Clear the work_flow_link field
        instance.work_flow_link = []
        instance.save()
        return instance
