from acr_tool.models import *
from django.db.models import Max
from django.utils.timezone import now
from rest_framework import serializers


class RiskAssessmentInstructionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskAssessmentInstructions
        fields = ['id', 'instructions', 'created_by', 'created_at']
        read_only_fields = ['created_by', 'created_at']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        instance.instructions = validated_data.get('instructions', instance.instructions)
        instance.save()
        return instance


class RiskAssessmentSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskAssessmentSection
        fields = '__all__'
        read_only_fields = ['id', 'created_by', 'created_at', 'section_order']


class RiskAssessmentQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskAssessmentQuestion
        fields = '__all__'
        read_only_fields = ['id', 'created_by', 'created_at', 'question_order']

    def validate(self, attrs):
        errors = []
        yes_score = attrs.get('yes_score', None)
        no_score = attrs.get('no_score', None)

        # Validate yes_score
        if yes_score is not None and (yes_score < 0 or yes_score > 10):
            errors.append("yes_score must be between 0 and 10.")

        # Validate no_score
        if no_score is not None and (no_score < 0 or no_score > 10):
            errors.append("no_score must be between 0 and 10.")

        if errors:
            if len(errors) == 2:  # Both fields are invalid
                raise serializers.ValidationError({"error": "yes_score and no_score both must be between 0 and 10."})
            else:
                raise serializers.ValidationError({"error": " ".join(errors)})

        return attrs


class RiskAssessmentQuestionInputSerializer(RiskAssessmentQuestionSerializer):
    class Meta:
        model = RiskAssessmentQuestion
        fields = ['question', 'yes_score', 'no_score']


class SectionWithQuestionsSerializer(serializers.ModelSerializer):
    question_data = RiskAssessmentQuestionInputSerializer(write_only=True)

    class Meta:
        model = RiskAssessmentSection
        fields = ['section', 'question_data']

    def validate(self, attrs):
        question_data = attrs.get('question_data', {})
        question_serializer = RiskAssessmentQuestionInputSerializer(data=question_data)

        # Validate the nested question serializer
        if not question_serializer.is_valid(raise_exception=False):
            raise serializers.ValidationError(
                {"error": question_serializer.errors.get('error', ["Invalid question data."])})

        return attrs

    def create(self, validated_data):
        question_data = validated_data.pop('question_data')
        section = RiskAssessmentSection.objects.create(**validated_data)

        max_order = RiskAssessmentQuestion.objects.filter(section=section).aggregate(
            Max('question_order')
        )['question_order__max']
        next_order = (max_order or 0) + 1

        # Get the logged-in user
        user = self.context['request'].user

        # Create the associated question with the section reference and created_by
        RiskAssessmentQuestion.objects.create(
            section=section,
            question_order=next_order,
            created_by=user,
            **question_data
        )

        return section


class RiskAssessmentOrgQuestionResponseSerializer(serializers.ModelSerializer):
    year = serializers.IntegerField(write_only=True, required=True)
    section_order = serializers.IntegerField(read_only=True)
    question_order = serializers.IntegerField(read_only=True)

    class Meta:
        model = RiskAssessmentOrgQuestionResponse
        fields = ['organization', 'section', 'question', 'response', 'response_score', 'note', 'comment',
                  'created_by', 'created_at', 'year', 'section_order', 'question_order']
        read_only_fields = ['organization', 'section', 'question', 'response', 'response_score', 'note',
                            'comment', 'created_by', 'created_at', 'section_order', 'question_order']

    def validate_year(self, value):
        current_year = now().year
        if value > current_year:
            raise serializers.ValidationError(f"Future years are not allowed.")
        return value

    def validate(self, data):
        # Ensure only one record exists for a section-question combination per organization per year
        organization = data.get('organization')
        section = data.get('section')
        question = data.get('question')
        year = data.get('year')

        existing = RiskAssessmentOrgQuestionResponse.objects.filter(
            organization=organization,
            section=section,
            question=question,
            created_at__year=year
        ).first()

        if existing:
            raise serializers.ValidationError(
                "A record for this organization, section, and question already exists for this year.")

        return data


class RiskAssessmentOrgQuestionResponsePartialUpdateSerializer(serializers.Serializer):
    section_id = serializers.IntegerField()
    question_id = serializers.IntegerField()
    year = serializers.IntegerField(write_only=True)
    response_score = serializers.IntegerField(required=False)
    response = serializers.BooleanField(required=False)
    note = serializers.CharField(required=False, allow_blank=True)
    comment = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        response_score = data.get('response_score')
        response = data.get('response')

        # Validate response_score range
        if response_score is not None and (response_score < 0 or response_score > 10):
            raise serializers.ValidationError("response_score must be between 0 and 10.")

        # Validate the correlation between response and response_score
        if response_score is not None and response is None:
            raise serializers.ValidationError("response is required when response_score is provided.")
        if response is not None and response_score is None:
            raise serializers.ValidationError("response_score is required when response is provided.")

        return data

    def update(self, instance, validated_data):
        # Update instance fields
        instance.response_score = validated_data.get('response_score', instance.response_score)
        instance.response = validated_data.get('response', instance.response)
        instance.note = validated_data.get('note', instance.note)
        instance.comment = validated_data.get('comment', instance.comment)
        instance.save()
        return instance
