from rest_framework import viewsets, status
from rest_framework.response import Response
from fiduciary.models import *
from fiduciary.serializers import *
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from utils.s3_utils import upload_file_to_s3_folder
from rest_framework.permissions import AllowAny, IsAuthenticated

from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives 
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from fiduciary.swagger_schema import  *
from rest_framework import serializers

# Retrospective Review Views
class RetrospectiveKeyReviewQuestionViewSet(viewsets.ModelViewSet):
    queryset = RetrospectiveKeyReviewQuestion.objects.all()
    serializer_class = RetrospectiveKeyReviewQuestionSerializer
    swagger_schema =  RetrospectiveKeyReviewQuestionSwaggerAutoSchema


    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response({
                "status": "success",
                "message": "Question created successfully.",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "status": "error",
                "message": "There was an error creating the question.",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)


    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if serializer.is_valid():
            self.perform_update(serializer)
            return Response({
                "status": "success",
                "message": "Question updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "status": "error",
                "message": "There was an error updating the question.",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            "status": "success",
            "message": "Question deleted successfully."
        }, status=status.HTTP_204_NO_CONTENT)



class RetrospectiveReviewViewSet(viewsets.ModelViewSet):
    queryset = FiduciaryReport.objects.all()
    serializer_class = RetrospectiveReviewSerializer
    permission_classes = [IsAuthenticated]
    swagger_schema = RetrospectiveReviewSwaggerAutoSchema

    @action(detail=False, methods=['get'], url_path='review-by-year')
    def get_reviews_by_year(self, request, year=None):
        """
        Custom endpoint to retrieve retrospective review data by year.
        """
        if not year:
            return Response({
                "status": "error",
                "message": "Year of report is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        user = request.user

        # Apply role-based filtering for reports
        if user.role == 'CCO':
            fiduciary_reports = FiduciaryReport.objects.filter(created_at__year=year, is_draft=False)
        else:
            fiduciary_reports = FiduciaryReport.objects.filter(created_at__year=year, user=user, is_draft=False)

        # Initialize response data for reports
        response_data = []

        # Prepare the key review questions and answers for the response
        questions_and_answers = []
        key_questions = RetrospectiveKeyReviewQuestion.objects.all()
        
        # If there are no fiduciary reports for the user/year, still return key questions and answers
        if not fiduciary_reports.exists():
            for question in key_questions:
                # Get the answer for the specific user and year, if it exists
                try:
                    answer = RetrospectiveKeyReviewAnswer.objects.get(
                        question=question,
                        year_of_report=year,
                        user=user  # Ensure the answer is linked to the logged-in user
                    )
                    questions_and_answers.append({
                        "id": question.id,
                        "question": question.question_text,
                        "answer": answer.answer
                    })
                except RetrospectiveKeyReviewAnswer.DoesNotExist:
                    # If no answer exists, return None for the answer field
                    questions_and_answers.append({
                        "id": question.id,
                        "question": question.question_text,
                        "answer": None
                    })

            # Retrieve the general notes for the year for the user (if any)
            general_notes_instance = RetrospectiveKeyReviewAnswer.objects.filter(
                year_of_report=year,
                user=user
            ).exclude(notes__isnull=True).first()

            general_notes = general_notes_instance.notes if general_notes_instance else None

            # Return only key review questions and an empty report data field
            return Response({
                "status": "success",
                "message": f"No reports found for the specified year {year}. Returning key review questions and answers.",
                "data": {
                    "key_review_questions": {
                        "notes": general_notes,
                        "questions": questions_and_answers
                    },
                    "reports": []  # Empty report data
                }
            }, status=status.HTTP_200_OK)

        # If reports exist, fetch them and prepare the response
        for report in fiduciary_reports:
            previous_plan_service = report.plan_services.filter(current_plan=True).first()
            recommended_plan_service = report.plan_services.filter(recommended_ira=True).first()

            previous_plan_type = previous_plan_service.general_plan_service.service_name if previous_plan_service else None
            recommended_plan_type = recommended_plan_service.general_plan_service.service_name if recommended_plan_service else None

            report_file_url = report.s3_file_link if report.s3_file_link else None

            # Safely access client details and other related fields
            client_details = getattr(report, 'client_details', None)
            first_name = client_details.first_name if client_details else None
            last_name = client_details.last_name if client_details else None

            # Additional fields to check (you can add more if necessary)
            disclosures_delivered = report.disclosures_delivered
            alternative_plans_presented = report.alternative_plans_presented
            fee_services_analysis = report.fee_services_analysis
            best_interest_recommendation = report.best_interest_recommendation
            notes = report.notes

            # Add report-specific data to the response
            response_data.append({
                "report_id": report.id,
                "report_file": report_file_url,
                "first_name": first_name,
                "last_name": last_name,
                "previous_plan_type": previous_plan_type,
                "recommended_plan_type": recommended_plan_type,
                "created_at": report.created_at,
                "disclosures_delivered": disclosures_delivered,
                "alternative_plans_presented": alternative_plans_presented,
                "fee_services_analysis": fee_services_analysis,
                "best_interest_recommendation": best_interest_recommendation,
                "notes": notes
            })

        # Get the key review answers for the year specific to the user
        for question in key_questions:
            try:
                # Check if there is an answer for each question for the user and year
                answer = RetrospectiveKeyReviewAnswer.objects.get(
                    question=question,
                    year_of_report=year,
                    user=user  # Ensure the answer is tied to the logged-in user
                )
                questions_and_answers.append({
                    "id": question.id,
                    "question": question.question_text,
                    "answer": answer.answer
                })
            except RetrospectiveKeyReviewAnswer.DoesNotExist:
                # If no answer exists, return None for the answer field
                questions_and_answers.append({
                    "id": question.id,
                    "question": question.question_text,
                    "answer": None
                })

        # Retrieve the general notes for the year specific to the user
        general_notes_instance = RetrospectiveKeyReviewAnswer.objects.filter(
            year_of_report=year,
            user=user
        ).exclude(notes__isnull=True).first()

        general_notes = general_notes_instance.notes if general_notes_instance else None

        # Return the response with both the report data and review questions/answers, along with the general notes
        return Response({
            "status": "success",
            "message": f"Reports for year {year} retrieved successfully.",
            "data": {
                "key_review_questions": {
                    "notes": general_notes,  # Include the general notes for the year specific to the user
                    "questions": questions_and_answers  # List of questions and answers
                },
                "reports": response_data,
            }
        }, status=status.HTTP_200_OK)




class RetrospectiveKeyReviewAnswerViewSet(viewsets.ModelViewSet):
    queryset = RetrospectiveKeyReviewAnswer.objects.all()
    serializer_class = KeyReviewAnswerUpdateSerializer
    permission_classes = [IsAuthenticated]
    swagger_schema =  RetrospectiveKeyReviewQuestionSwaggerAutoSchema

    @action(detail=False, methods=['put'])
    def update_answers_and_notes(self, request):
        """
        Custom endpoint to update the key review answers and notes for a given year.
        """
        # Use a single serializer that accepts both answers and notes
        serializer = KeyReviewAnswerUpdateSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            # Extract validated data
            year = serializer.validated_data.get('year')
            notes = serializer.validated_data.get('notes')
            key_review_questions = serializer.validated_data.get('key_review_questions', [])
            user = request.user  # Get the logged-in user

            # Update or create key review answers based on the provided questions and year
            updated_answers = []
            for qa in key_review_questions:
                question_id = qa.get("question_id")
                answer_value = qa.get("answer", False)

                try:
                    # Fetch the question and ensure it exists
                    question = RetrospectiveKeyReviewQuestion.objects.get(id=question_id)

                    # Update or create the answer for the given question, year, and user
                    review_answer, created = RetrospectiveKeyReviewAnswer.objects.update_or_create(
                        year_of_report=year,
                        question=question,
                        user=user,  # Ensure the answer is tied to the correct user
                        defaults={"answer": answer_value, "notes": notes}  # Include notes in the defaults
                    )

                    # Prepare response data for updated answers
                    updated_answers.append({
                        "question_id": question.id,
                        "question_text": question.question_text,
                        "answer": review_answer.answer,
                    })

                except RetrospectiveKeyReviewQuestion.DoesNotExist:
                    return Response({
                        "status": "error",
                        "message": f"Question with ID {question_id} does not exist."
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Batch update the notes for all answers related to the given year and user
            if notes is not None:
                RetrospectiveKeyReviewAnswer.objects.filter(year_of_report=year, user=user).update(notes=notes)

            # Return a combined response for answers and notes
            return Response({
                "status": "success",
                "message": f"Key review answers and notes for the year {year} updated successfully.",
                "data": {
                    "year": year,
                    "notes": notes,
                    "key_review_answers": updated_answers
                }
            }, status=status.HTTP_200_OK)

        else:
            # Return error response if the serializer is not valid
            return Response({
                "status": "error",
                "message": "There was an error updating the key review answers and notes.",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)