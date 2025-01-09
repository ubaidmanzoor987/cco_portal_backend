from datetime import datetime
from acr_tool.models import *
from rest_framework import serializers


class AnnualReportInstructionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnnualReportInstructions
        fields = ['id', 'instructions', 'background', 'overview_crp', 'regulatory_developments', 'work_completed',
                  'test_conducted', 'conclusion', 'created_by', 'created_at']
        read_only_fields = ['created_by', 'created_at']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        instance.instructions = validated_data.get('instructions', instance.instructions)
        instance.background = validated_data.get('background', instance.background)
        instance.overview_crp = validated_data.get('overview_crp', instance.overview_crp)
        instance.regulatory_developments = validated_data.get('regulatory_developments',
                                                              instance.regulatory_developments)
        instance.work_completed = validated_data.get('work_completed', instance.work_completed)
        instance.test_conducted = validated_data.get('test_conducted', instance.test_conducted)
        instance.conclusion = validated_data.get('conclusion', instance.conclusion)
        instance.save()
        return instance


class AnnualReportSerializer(serializers.ModelSerializer):
    blank_page = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField(max_length=255, allow_blank=True),
        ),
        allow_empty=True,
        required=False
    )

    class Meta:
        model = AnnualReport
        fields = '__all__'
        read_only_fields = ['organization', 'created_by', 'created_at']

    def validate_blank_page(self, value):
        """Ensure each item in the blank_page list has the required fields."""
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError("Each item in blank_page must be a dictionary.")
            if "page_order" not in item:
                raise serializers.ValidationError("Each dictionary must contain 'page_order' field.")

            # Validate page_order is an integer
            if not isinstance(item['page_order'], str):
                raise serializers.ValidationError("The 'page_order' must be a string.")

            # Validate page_text is a string
            if not isinstance(item['page_text'], str):
                raise serializers.ValidationError("The 'page_text' must be a string.")

        return value


class PDFToWordSerializer(serializers.Serializer):
    pdf_file = serializers.FileField(required=True)
