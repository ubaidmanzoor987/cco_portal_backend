from acr_tool.models import *
from datetime import datetime
from rest_framework import serializers


class ComplianceMeetingInstructionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceMeetingInstructions
        fields = ['id', 'instructions', 'overview', 'created_by', 'created_at']
        read_only_fields = ['created_by', 'created_at']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        instance.instructions = validated_data.get('instructions', instance.instructions)
        instance.overview = validated_data.get('overview', instance.overview)  # Updated field name
        instance.save()
        return instance


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceMeetingQuestion
        fields = ['id', 'content']


class TopicSerializer(serializers.ModelSerializer):
    questions_data = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = ComplianceMeetingTopic
        fields = ['id', 'topic', 'created_at', 'questions_data', 'questions']

    def create(self, validated_data):
        questions_data = validated_data.pop('questions_data', [])
        user = self.context['request'].user
        topic = ComplianceMeetingTopic.objects.create(created_by=user, **validated_data)

        if questions_data:
            for question_content in questions_data:
                ComplianceMeetingQuestion.objects.create(topic=topic, created_by=user, content=question_content)

        return topic

    def update(self, instance, validated_data):
        questions_data = validated_data.pop('questions_data', [])
        instance.topic = validated_data.get('topic', instance.topic)
        instance.save()

        if questions_data:
            # Update existing questions
            existing_questions = {q.id: q for q in instance.questions.all()}
            new_questions = {i: content for i, content in enumerate(questions_data)}

            for i, question_content in new_questions.items():
                if i in existing_questions:
                    question = existing_questions.pop(i)
                    question.content = question_content
                    question.save()
                else:
                    ComplianceMeetingQuestion.objects.create(
                        topic=instance, created_by=self.context['request'].user, content=question_content
                    )

            # Delete questions that are no longer in the update data
            for question in existing_questions.values():
                question.delete()

        return instance


class ComplianceMeetingTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceMeetingTopic
        fields = ['id', 'topic', 'created_at']


class ComplianceMeetingDataSerializer(serializers.Serializer):
    topic_id = serializers.IntegerField()
    sample_questions = serializers.ListField(child=serializers.IntegerField())
    custom_questions = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    comment = serializers.CharField(allow_blank=True)


class ComplianceMeetingSerializer(serializers.ModelSerializer):
    compliance_meeting_data = serializers.ListField(child=ComplianceMeetingDataSerializer(), write_only=True)

    class Meta:
        model = ComplianceMeeting
        fields = ['compliance_meeting_data']

    def validate_compliance_meeting_data(self, value):
        """
        Validate that the topic IDs and sample questions are valid.
        """
        for item in value:
            topic_id = item.get('topic_id')  # Use topic_id instead of topic
            sample_question_ids = item.get('sample_questions')

            # Check if the topic ID exists in ComplianceMeetingTopic
            if not ComplianceMeetingTopic.objects.filter(id=topic_id).exists():
                raise serializers.ValidationError(f"Topic ID {topic_id} is invalid.")

            # Check if the sample questions exist
            questions = ComplianceMeetingQuestion.objects.filter(id__in=sample_question_ids)
            if len(questions) != len(sample_question_ids):
                raise serializers.ValidationError(f"One or more sample questions in {sample_question_ids} are invalid.")

        return value

    def create(self, validated_data):
        compliance_meeting_data = validated_data.pop('compliance_meeting_data')
        user = self.context['request'].user
        current_year = datetime.now().year

        # Check if a ComplianceMeeting record already exists for the current year
        existing_record = ComplianceMeeting.objects.filter(
            created_at__year=current_year,
            organization=self._get_organization(user)
        ).first()

        if existing_record:
            raise serializers.ValidationError(f"A ComplianceMeeting record already exists for the year {current_year}.")

        # Create the ComplianceMeeting
        compliance_meeting = ComplianceMeeting.objects.create(
            created_by=user,
            organization=self._get_organization(user)
        )

        # Create the relationship between meeting and topics along with custom questions and comments
        for data in compliance_meeting_data:
            topic_id = data['topic_id']  # Use topic_id instead of topic
            sample_question_ids = data['sample_questions']
            custom_questions = data['custom_questions']
            comment = data['comment']

            # Create the ComplianceMeetingTopicDetail entry
            topic = ComplianceMeetingTopic.objects.get(id=topic_id)
            topic_detail = ComplianceMeetingTopicDetail.objects.create(
                meeting=compliance_meeting,
                topic=topic,
                custom_questions=custom_questions,
                comment=comment
            )

            # Add sample questions to the meeting
            questions = ComplianceMeetingQuestion.objects.filter(id__in=sample_question_ids)
            compliance_meeting.sample_questions.add(*questions)

        compliance_meeting.save()
        return compliance_meeting

    def update(self, instance, validated_data):
        compliance_meeting_data = validated_data.pop('compliance_meeting_data', [])

        # Clear existing relationships
        instance.sample_questions.clear()
        instance.topic_details.all().delete()  # Remove previous custom questions and comments

        for data in compliance_meeting_data:
            topic_id = data['topic_id']  # Use topic_id instead of topic
            sample_question_ids = data['sample_questions']
            custom_questions = data['custom_questions']
            comment = data['comment']

            # Create new topic detail
            topic = ComplianceMeetingTopic.objects.get(id=topic_id)
            topic_detail = ComplianceMeetingTopicDetail.objects.create(
                meeting=instance,
                topic=topic,
                custom_questions=custom_questions,
                comment=comment
            )

            # Add sample questions to the meeting
            questions = ComplianceMeetingQuestion.objects.filter(id__in=sample_question_ids)
            instance.sample_questions.add(*questions)

        instance.save()
        return instance

    def _get_organization(self, user):
        if user.is_superuser:
            return None
        return user.organization


class ComplianceMeetingQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceMeetingQuestion
        fields = ['id', 'content']


class MeetingTopicWithQuestionsSerializer(serializers.ModelSerializer):
    topic_id = serializers.IntegerField(source='id')  # Map 'id' to 'topic_id'
    sample_questions = serializers.SerializerMethodField()
    custom_questions = serializers.SerializerMethodField()
    comment = serializers.SerializerMethodField()

    class Meta:
        model = ComplianceMeetingTopic
        fields = ['topic_id', 'topic', 'sample_questions', 'custom_questions', 'comment']

    def get_sample_questions(self, topic):
        # Get the sample questions associated with this topic and meeting
        meeting = self.context['meeting']
        questions = ComplianceMeetingQuestion.objects.filter(
            compliance_meetings=meeting, topic=topic
        )
        return ComplianceMeetingQuestionSerializer(questions, many=True).data

    def get_custom_questions(self, topic):
        # Get the custom questions for this topic and meeting from ComplianceMeetingTopicDetail
        meeting = self.context['meeting']
        try:
            topic_detail = ComplianceMeetingTopicDetail.objects.get(meeting=meeting, topic=topic)
            return topic_detail.custom_questions
        except ComplianceMeetingTopicDetail.DoesNotExist:
            return []

    def get_comment(self, topic):
        # Get the comment for this topic and meeting from ComplianceMeetingTopicDetail
        meeting = self.context['meeting']
        try:
            topic_detail = ComplianceMeetingTopicDetail.objects.get(meeting=meeting, topic=topic)
            return topic_detail.comment
        except ComplianceMeetingTopicDetail.DoesNotExist:
            return ""


class ComplianceMeetingDetailSerializer(serializers.ModelSerializer):
    topics = serializers.SerializerMethodField()

    class Meta:
        model = ComplianceMeeting
        fields = ['id', 'topics', 'organization', 'created_by', 'created_at']

    def get_topics(self, meeting):
        # Get the topics associated with this meeting, including custom questions and comments
        topics = meeting.topics.all()
        return MeetingTopicWithQuestionsSerializer(topics, many=True, context={'meeting': meeting}).data
