# Retrospective Review
from rest_framework import serializers
from fiduciary.models import RetrospectiveKeyReviewQuestion, RetrospectiveKeyReviewAnswer

class RetrospectiveKeyReviewQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetrospectiveKeyReviewQuestion
        fields = ['id', 'question_text', 'is_required']


class RetrospectiveKeyReviewAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetrospectiveKeyReviewAnswer
        fields = ['id', 'question', 'answer']


class RetrospectiveReviewSerializer(serializers.Serializer):
    year_of_report = serializers.IntegerField()
    key_review_questions = RetrospectiveKeyReviewAnswerSerializer(many=True)

    class Meta:
        fields = ['year_of_report', 'key_review_questions']


class QuestionAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    answer = serializers.BooleanField()




class KeyReviewAnswerUpdateSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    key_review_questions = QuestionAnswerSerializer(many=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)  # Include notes field

    def validate_year(self, value):
        # Validate the year field if necessary
        if value < 2000 or value > 2100:  # Example validation condition
            raise serializers.ValidationError({
                "status": "error",
                "message": "The year must be between 2000 and 2100."
            })
        return value

    def validate(self, attrs):
        # Ensure that either key_review_questions or notes is provided
        if not attrs.get('key_review_questions') and attrs.get('notes') is None:
            raise serializers.ValidationError({
                "status": "error",
                "message": "Either key review questions or notes must be provided."
            })
        return attrs

    def update(self, instance, validated_data):
        year = validated_data.get('year')
        key_review_questions = validated_data.get('key_review_questions', [])
        notes = validated_data.get('notes')
        user = self.context['request'].user  # Get the user from the request context

        # Process and update key review questions
        question_responses = []
        for qa in key_review_questions:
            question_id = qa.get("question_id")
            answer_value = qa.get("answer", False)

            try:
                # Ensure the question exists before proceeding
                question = RetrospectiveKeyReviewQuestion.objects.get(id=question_id)

                # Update or create the answer for the given question, year, and user
                review_answer, created = RetrospectiveKeyReviewAnswer.objects.update_or_create(
                    year_of_report=year,
                    question=question,
                    user=user,  # Include the user field in the lookup
                    defaults={"answer": answer_value}
                )

                # Append each question response to include in the final response
                question_responses.append({
                    "question_id": question.id,
                    "question_text": question.question_text,
                    "answer": review_answer.answer
                })

            except RetrospectiveKeyReviewQuestion.DoesNotExist:
                raise serializers.ValidationError({
                    "status": "error",
                    "message": f"Question with ID {question_id} does not exist."
                })

        # If notes are provided, update the notes for all answers related to the given year and user
        if notes is not None:
            RetrospectiveKeyReviewAnswer.objects.filter(year_of_report=year, user=user).update(notes=notes)

        # Construct the final response data
        return {
            "year": year,
            "notes": notes,
            "questions": question_responses 
        }

        