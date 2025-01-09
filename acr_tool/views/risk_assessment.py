from datetime import datetime

from django.db.models import Max
from django.db import IntegrityError
from django.utils.timezone import now

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, viewsets, serializers
from rest_framework.authentication import TokenAuthentication

from acr_tool.models import *
from acr_tool.serializers import *
from acr_tool.permissions import *
from acr_tool.swagger_schema import *


class RiskAssessmentInstructionsViewSet(viewsets.ModelViewSet):
    queryset = RiskAssessmentInstructions.objects.all()
    serializer_class = RiskAssessmentInstructionsSerializer
    authentication_classes = [TokenAuthentication]
    swagger_schema = RiskAssessmentInstructionsSwaggerAutoSchema

    def get_permissions(self):
        # Allow both superuser for create, update, destroy actions and CCO for retrieve actions
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsSuperUser]
        else:  # For retrieve and list actions
            permission_classes = [IsSuperUserOrCCO]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        return RiskAssessmentInstructions.objects.all()  # Allow retrieval of all instances

    def perform_create(self, serializer):
        if RiskAssessmentInstructions.objects.exists():
            raise serializers.ValidationError({"detail": "Only one record is allowed."})
        else:
            serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save()


class RiskAssessmentSectionViewSet(viewsets.ModelViewSet):
    queryset = RiskAssessmentSection.objects.all()
    serializer_class = RiskAssessmentSectionSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    swagger_schema = RiskAssessmentSectionSwaggerAutoSchema

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperUser()]
        return super().get_permissions()

    # Override the destroy method to handle the section_order reordering after deletion
    def destroy(self, request, *args, **kwargs):
        # Get the section to be deleted
        instance = self.get_object()

        # Perform the deletion
        self.perform_destroy(instance)

        # After deletion, update the section_order of remaining sections
        remaining_sections = RiskAssessmentSection.objects.all().order_by('section_order')

        for index, section in enumerate(remaining_sections, start=1):
            section.section_order = index
            section.save()

        return Response({"detail": "Section deleted successfully."}, status=status.HTTP_200_OK)


class SectionWithQuestionViewSet(viewsets.ModelViewSet):
    queryset = RiskAssessmentSection.objects.all()
    serializer_class = SectionWithQuestionsSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    swagger_schema = RiskAssessmentSectionSwaggerAutoSchema

    def get_permissions(self):
        if self.action == 'create':
            return [IsSuperUser()]
        return super().get_permissions()

    def perform_create(self, serializer):
        max_order = RiskAssessmentSection.objects.aggregate(Max('section_order'))['section_order__max']
        next_order = (max_order or 0) + 1
        serializer.save(created_by=self.request.user, section_order=next_order)


class RiskAssessmentQuestionViewSet(viewsets.ModelViewSet):
    queryset = RiskAssessmentQuestion.objects.all()
    serializer_class = RiskAssessmentQuestionSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    swagger_schema = RiskAssessmentQuestionSwaggerAutoSchema

    # Define custom permissions for create/update/delete actions
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperUser()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
        except IntegrityError:
            raise ValidationError({"detail": "A question with this text already exists in the specified section."})
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        section = serializer.validated_data.get('section')
        max_order = RiskAssessmentQuestion.objects.filter(section=section).aggregate(
            Max('question_order')
        )['question_order__max']
        next_order = (max_order or 0) + 1
        serializer.save(created_by=self.request.user, question_order=next_order)

    def destroy(self, request, *args, **kwargs):
        # Get the question to be deleted
        instance = self.get_object()
        section = instance.section

        # Perform the deletion
        self.perform_destroy(instance)

        # After deletion, update the question_order of remaining questions in the same section
        remaining_questions = RiskAssessmentQuestion.objects.filter(section=section).order_by('question_order')

        for index, question in enumerate(remaining_questions, start=1):
            question.question_order = index
            question.save()

        return Response({"detail": "Question deleted successfully."}, status=status.HTTP_200_OK)


def calculate_and_store_average_scores(organization, created_by, year):
    sections = RiskAssessmentSection.objects.all()

    for section in sections:
        # Filter responses by section, organization, and year
        responses = RiskAssessmentOrgQuestionResponse.objects.filter(
            section=section,
            created_at__year=year,
            organization=organization
        )

        if responses.exists():
            # Calculate the average score for the section and round it to one decimal place
            total_score = sum(response.response_score for response in responses)
            average_score = round(total_score / responses.count(), 1)

            # Try to update or create the average score record
            obj, created = RiskAssessmentOrgAverageScore.objects.update_or_create(
                section=section,
                created_at__year=year,
                organization=organization,
                defaults={'average_score': average_score}
            )

            if created:
                # If the record was created, set the organization and created_by fields
                obj.organization = organization if organization else None
                obj.created_by = created_by
                obj.save()


def spread_policies_and_procedures(organization, section_question_pairs, current_year):
    # Step 1: Create or update PoliciesAndProcedures records for questions with scores of 7 or above
    for pair in section_question_pairs:
        section_id = pair['section_id']
        question_id = pair['question_id']

        # Check the response score for the given section and question
        try:
            # Fetch the RiskAssessmentOrgQuestionResponse object
            response_obj = RiskAssessmentOrgQuestionResponse.objects.get(
                section_id=section_id,
                question_id=question_id,
                created_at__year=current_year,
                organization=organization
            )

            # Check if the response score is >= 7
            if response_obj.response_score >= 7:
                # Create or update the PoliciesAndProcedures record using the response_obj
                PoliciesAndProcedures.objects.update_or_create(
                    risk_assessment_response=response_obj,
                    defaults={
                        'organization': organization,
                        'policies_procedure_tab': 'riskAssessment'  # You can adjust this field as needed
                    }
                )
        except RiskAssessmentOrgQuestionResponse.DoesNotExist:
            # Skip if no response object exists for this section and question
            continue

    # Step 2: Remove records for questions with response scores less than 7 for the current year
    low_score_questions = RiskAssessmentOrgQuestionResponse.objects.filter(
        response_score__lt=7,
        created_at__year=current_year,
        organization=organization
    ).values_list('question_id', flat=True).distinct()

    # Remove records from PoliciesAndProcedures for those questions in the current year
    deleted_count, _ = PoliciesAndProcedures.objects.filter(
        risk_assessment_response__question_id__in=low_score_questions,
        created_at__year=current_year,
        organization=organization
    ).delete()

    return deleted_count


class RiskAssessmentOrgQuestionResponseViewSet(viewsets.ModelViewSet):
    queryset = RiskAssessmentOrgQuestionResponse.objects.all()
    serializer_class = RiskAssessmentOrgQuestionResponseSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    swagger_schema = RiskAssessmentOrgQuestionResponseSwaggerAutoSchema

    def get_queryset(self):
        # Get the current year and the organization from the logged-in user
        current_year = now().year
        if self.request.user.is_superuser:
            return RiskAssessmentOrgQuestionResponse.objects.filter(
                created_at__year=current_year
            )
        else:
            return RiskAssessmentOrgQuestionResponse.objects.filter(
                organization=self.request.user.organization,
                created_at__year=current_year
            )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        year = serializer.validated_data.get('year')
        current_year = now().year

        # Determine organization and created_by
        organization = None if request.user.is_superuser else request.user.organization
        created_by = request.user

        sections = RiskAssessmentSection.objects.all()

        # Retrieve existing responses for the given year and organization
        existing_responses = RiskAssessmentOrgQuestionResponse.objects.filter(
            created_at__year=year,
            organization=organization
        ).select_related('section', 'question')

        if year < current_year:
            if not existing_responses.exists():
                return Response({"detail": f"No records found for the year {year}."}, status=status.HTTP_404_NOT_FOUND)
            return self.prepare_response(existing_responses)

        # Create new responses for the current year only if they don't exist already
        created_responses = []
        for section in sections:
            questions = RiskAssessmentQuestion.objects.filter(section=section)
            for question in questions:
                if not existing_responses.filter(section=section, question=question).exists():
                    response_data = {
                        'organization': organization,
                        'section': section,
                        'question': question,
                        'response_score': -1,
                        'created_by': created_by,
                        'section_order': section.section_order,
                        'question_order': question.question_order,
                    }
                    created_responses.append(response_data)

        # Bulk create new records that don't exist yet
        RiskAssessmentOrgQuestionResponse.objects.bulk_create([
            RiskAssessmentOrgQuestionResponse(
                organization=response['organization'],
                section=response['section'],
                question=response['question'],
                response_score=response['response_score'],
                created_by=response['created_by'],
                created_at=now(),
            )
            for response in created_responses
        ])

        # Merge existing and newly created responses
        all_responses = list(existing_responses) + [
            RiskAssessmentOrgQuestionResponse(
                organization=response['organization'],
                section=response['section'],
                question=response['question'],
                response_score=response['response_score'],
                created_by=response['created_by'],
            )
            for response in created_responses
        ]

        # Calculate and store average scores
        calculate_and_store_average_scores(organization, created_by, year)

        return self.prepare_response(all_responses, year, organization)

    def prepare_response(self, responses, year, organization):
        section_data = {}
        for response in responses:
            if response.created_at is None:
                continue

            section_id = response.section.id
            if section_id not in section_data:
                section_data[section_id] = {
                    'section_id': section_id,
                    'section': response.section.section,
                    'section_order': response.section.section_order,
                    'average_score': self.get_average_score(response.section, year, organization),
                    'questions': []
                }
            section_data[section_id]['questions'].append({
                'question_id': response.question.id,
                'question': response.question.question,
                'response_score': response.response_score,
                'response': response.response,
                'note': response.note,
                'comment': response.comment,
                'yes_score': response.question.yes_score,
                'no_score': response.question.no_score,
                'created_at': response.created_at,
                'year': response.created_at.year,
                'question_order': response.question.question_order,
            })

        # Sort section_data by section_id
        sorted_section_data = sorted(section_data.values(), key=lambda x: x['section_id'])

        # Sort questions within each section by question_id
        for section in sorted_section_data:
            section['questions'] = sorted(section['questions'], key=lambda x: x['question_id'])

        return Response(sorted_section_data, status=status.HTTP_201_CREATED)

    def get_average_score(self, section, year, organization):
        try:
            return RiskAssessmentOrgAverageScore.objects.get(
                section=section,
                created_at__year=year,
                organization=organization,
            ).average_score
        except RiskAssessmentOrgAverageScore.DoesNotExist:
            return None

    @action(detail=False, methods=['get'], url_path='reset-section/(?P<section_id>\d+)')
    def reset_section(self, request, section_id=None):
        if not section_id:
            return Response({"detail": "section_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate if the section exists
        try:
            section = RiskAssessmentSection.objects.get(id=section_id)
        except RiskAssessmentSection.DoesNotExist:
            return Response({"detail": "Section not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get the current year
        current_year = now().year

        # Determine organization and created_by
        if request.user.is_superuser:
            organization = None
        else:
            organization = request.user.organization
        created_by = request.user

        # Fetch records for the given section_id and current year
        records = RiskAssessmentOrgQuestionResponse.objects.filter(
            section_id=section_id,
            created_at__year=current_year
        )

        if not records.exists():
            return Response(
                {"detail": f"No records found for section_id {section_id} in the current year {current_year}."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Update the records
        records.update(response=None, response_score=-1, note=None, comment=None)

        # Calculate and store average scores
        calculate_and_store_average_scores(organization, created_by, current_year)

        # Check and delete PoliciesAndProcedures records for the section
        deleted_count = self.delete_policies_and_procedures_for_section(section_id, current_year, organization)

        # Prepare a response with information about deleted records
        if deleted_count > 0:
            message = f"{deleted_count} PoliciesAndProcedures records for section_id {section_id} have been deleted."
        else:
            message = f"No PoliciesAndProcedures records found for section_id {section_id} in the current year."

        # Serialize and return the updated records
        serializer = self.get_serializer(records, many=True)
        return Response({"detail": message, "data": serializer.data}, status=status.HTTP_200_OK)

    def delete_policies_and_procedures_for_section(self, section_id, year, organization):
        policies_records = PoliciesAndProcedures.objects.filter(
            risk_assessment_response__section_id=section_id,
            created_at__year=year,
            policies_procedure_tab='riskAssessment',
            organization=organization
        )

        # Get the count of records to be deleted
        deleted_count = policies_records.count()

        # Delete the records
        policies_records.delete()

        # Return the count of deleted records
        return deleted_count


class RiskAssessmentOrgQuestionResponsePartialUpdateView(viewsets.ModelViewSet):
    queryset = RiskAssessmentOrgQuestionResponse.objects.all()
    serializer_class = RiskAssessmentOrgQuestionResponsePartialUpdateSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    swagger_schema = RiskAssessmentOrgQuestionResponseSwaggerAutoSchema

    def partial_update(self, request, *args, **kwargs):
        current_year = now().year

        # Determine organization and created_by
        if request.user.is_superuser:
            organization = None
        else:
            organization = request.user.organization
        created_by = request.user
        # Expecting a list of dictionaries
        if not isinstance(request.data, list):
            return Response({"detail": "Invalid data format, expected a list of objects."},
                            status=status.HTTP_400_BAD_REQUEST)

        errors = []
        updated_responses = []
        section_question_pairs = []

        for item in request.data:
            serializer = self.get_serializer(data=item)
            serializer.is_valid(raise_exception=True)

            section_id = serializer.validated_data.get('section_id')
            question_id = serializer.validated_data.get('question_id')
            year = serializer.validated_data.get('year')

            # Add the pair as a tuple or dictionary to the list
            section_question_pairs.append({'section_id': section_id, 'question_id': question_id})

            # Retrieve the record to update
            try:
                response_obj = RiskAssessmentOrgQuestionResponse.objects.get(
                    organization=organization,
                    section_id=section_id,
                    question_id=question_id,
                    created_at__year=year
                )
            except RiskAssessmentOrgQuestionResponse.DoesNotExist:
                errors.append(f"Record not found for section_id {section_id}, question_id {question_id}, year {year}")
                continue

            # Update the record
            serializer.update(response_obj, serializer.validated_data)
            updated_responses.append(response_obj)

        calculate_and_store_average_scores(organization, created_by, current_year)
        # Call the spread method to update the PoliciesAndProcedures table
        spread_policies_and_procedures(organization, section_question_pairs, current_year)

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        updated_data = RiskAssessmentOrgQuestionResponsePartialUpdateSerializer(updated_responses, many=True).data
        return Response({"updated_responses": updated_data}, status=status.HTTP_200_OK)
