from datetime import datetime
from collections import defaultdict

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import viewsets, status, generics, serializers

from acr_tool.models import *
from acr_tool.permissions import *
from acr_tool.serializers import *
from acr_tool.swagger_schema import *


class PoliciesAndProceduresInstructionsViewSet(viewsets.ModelViewSet):
    queryset = PoliciesAndProceduresInstructions.objects.all()
    serializer_class = PoliciesAndProceduresInstructionsSerializer
    authentication_classes = [TokenAuthentication]
    swagger_schema = PoliciesAndProceduresInstructionsSwaggerAutoSchema

    def get_permissions(self):
        # Allow both superuser for create, update, destroy actions and CCO for retrieve actions
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsSuperUser]
        else:  # For retrieve and list actions
            permission_classes = [IsSuperUserOrCCO]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        # Ensure that only one instance is returned
        return PoliciesAndProceduresInstructions.objects.all()

    def perform_create(self, serializer):
        # Check if a record already exists
        if PoliciesAndProceduresInstructions.objects.exists():
            raise serializers.ValidationError({"detail": "Only one record is allowed."})
        else:
            serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save()


class PoliciesAndProceduresViewSet(viewsets.ModelViewSet):
    queryset = PoliciesAndProcedures.objects.all()
    serializer_class = PoliciesAndProceduresSerializer
    parser_classes = (MultiPartParser, FormParser)
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsSuperUserOrCCO]
    swagger_schema = PoliciesAndProceduresSwaggerAutoSchema

    def get_queryset(self):
        current_year = datetime.utcnow().year
        # Filter PoliciesAndProcedures by current year and logged-in user's organization
        queryset = PoliciesAndProcedures.objects.filter(
            created_at__year=current_year,
            organization=self.request.user.organization
        )
        return queryset

    # Define the query parameter for swagger
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'policies_procedure_tab',
                openapi.IN_QUERY,
                description="The tab type for policies and procedures, e.g., 'ccoUpdates'",
                type=openapi.TYPE_STRING
            )
        ]
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        current_year = datetime.utcnow().year

        # Get the current serializer data
        serializer = self.get_serializer(instance)
        data = serializer.data

        # Check if the policies_procedure_tab is 'riskAssessment' and there is a related risk_assessment_response
        if instance.policies_procedure_tab == 'riskAssessment' and instance.risk_assessment_response:
            # Fetch the response details from RiskAssessmentOrgQuestionResponse for the current year
            response_data = instance.risk_assessment_response

            # Add the relevant fields to the response data
            data['note'] = response_data.note
            data['response_score'] = response_data.response_score
            data['response'] = response_data.response

        return Response(data)

    def create(self, request, *args, **kwargs):
        # Check if the user has CCO or SuperUser role
        if not request.user.is_superuser and request.user.role != 'CCO':
            return Response(
                {"error": "You do not have permission to create this record."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Extract policies_procedure_tab from query parameters
        policies_procedure_tab = request.query_params.get('policies_procedure_tab')

        if policies_procedure_tab != 'ccoUpdates':
            return Response(
                {"error": "Record creation is only allowed for 'ccoUpdates' in policies_procedure_tab."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Extract data from request
        cco_updates_text = request.data.get('cco_updates_text')

        # Check if 'cco_updates_text' is provided
        if not cco_updates_text:
            return Response(
                {"error": "'cco_updates_text' field is required when 'policies_procedure_tab' is 'ccoUpdates'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = request.data.copy()  # Make a mutable copy of the request data
        data['policies_procedure_tab'] = policies_procedure_tab

        # Now proceed with creating the record using the serializer
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()

        # Check if the instance was created in the current year
        current_year = datetime.utcnow().year
        if instance.created_at.year != current_year:
            return Response(
                {"error": "You can only update records created in the current year."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Automatically set the organization from the logged-in user
        if not request.user.is_superuser:
            serializer.validated_data['organization'] = request.user.organization

        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        # Check if the user has permission to delete
        if not request.user.is_superuser and request.user.role != 'CCO':
            raise PermissionDenied("You do not have permission to delete this record.")

        instance = self.get_object()
        self.perform_destroy(instance)

        # Return a custom response message
        return Response(
            {"detail": f"Policies and Procedures record deleted successfully."},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], url_path='current-year', url_name='current_year')
    def current_year(self, request):
        current_year = datetime.utcnow().year

        # Fetch only records for the current year and logged-in user's organization
        queryset = self.get_queryset()

        # Get average scores for the current year and logged-in user's organization
        average_scores = RiskAssessmentOrgAverageScore.objects.filter(
            created_at__year=current_year,
            organization=request.user.organization
        )

        section_scores = {avg_score.section.id: avg_score.average_score for avg_score in average_scores}

        # Prepare the response structure
        response_data = {
            'riskAssessment': [],
            'ccoUpdates': [],
            'regulatoryUpdates': {
                'regulatory_review': None,
                'rules': [],
            }
        }

        # Process riskAssessment records
        for record in queryset.filter(policies_procedure_tab='riskAssessment'):
            # Get the risk_assessment_response linked to PoliciesAndProcedures
            risk_assessment_response = record.risk_assessment_response

            # If there is a valid risk_assessment_response, get the section
            if risk_assessment_response:
                section_id = risk_assessment_response.section.id  # Get section ID from the response
            else:
                # If there is no response, handle the error or set default section_id (optional)
                section_id = None  # or some default section_id or handling logic

            average_score = section_scores.get(section_id, None)

            # Determine the risk category based on average score
            if average_score is not None:
                if 7 <= average_score <= 10:
                    risk_category = "High Risk Section"
                elif 5 <= average_score < 7:
                    risk_category = "Moderate Risk Section"
                else:  # 1 to 4.9
                    risk_category = "Low Risk Section"
            else:
                risk_category = "No Data"

            # Find or create the section in the response data
            section_data = next(
                (item for item in response_data['riskAssessment'] if item['risk_section'] == section_id), None)

            if section_data is None:
                # Create a new section entry
                section_data = {
                    'risk_section': section_id,
                    'risk_section_name': record.risk_assessment_response.section.section,  # Use section name
                    'risk_section_order': record.risk_assessment_response.section.section_order,  # Use section order
                    'risk_category': risk_category,
                    'average_score': average_score,
                    'risk_question': []
                }
                response_data['riskAssessment'].append(section_data)

            # Get the RiskAssessmentOrgQuestionResponse from the risk_assessment_response
            if risk_assessment_response:
                risk_assessment_data = risk_assessment_response
            else:
                risk_assessment_data = None

            # Append the question data to the risk_question list
            question_data = {
                'id': record.risk_assessment_response.question.id,
                'question_order': record.risk_assessment_response.question.question_order,
                'question': record.risk_assessment_response.question.question,
                'note': risk_assessment_data.note if risk_assessment_data else None,
                'response_score': risk_assessment_data.response_score if risk_assessment_data else None,
                'response': risk_assessment_data.response if risk_assessment_data else None,
                'policies_procedure_id': None
            }

            # Fetch the PoliciesAndProcedures data for the current question
            policies_record = PoliciesAndProcedures.objects.filter(
                risk_assessment_response=risk_assessment_response,  # Link using risk_assessment_response
                created_at__year=current_year,
                organization=request.user.organization
            ).first()

            if policies_record:
                # Add PoliciesAndProcedures related data to question data, including its ID
                question_data.update({
                    'policies_procedure_id': policies_record.id,
                    'policies_procedure_section': policies_record.policies_procedure_section,
                    'work_flow_link': policies_record.work_flow_link,
                    'work_flow_text': policies_record.work_flow_text,
                    'cco_updates_text': policies_record.cco_updates_text,
                    'reviewed_by': policies_record.reviewed_by,
                    'reviewed_date': policies_record.reviewed_date
                })

            section_data['risk_question'].append(question_data)

        # Process ccoUpdates records
        for record in queryset.filter(policies_procedure_tab='ccoUpdates'):
            response_data['ccoUpdates'].append(self.get_serializer(record).data)

        # Process regulatoryUpdates
        regulatory_updates = PoliciesAndProcedures.objects.filter(
            created_at__year=current_year,
            policies_procedure_tab='regulatoryUpdates',
            organization=request.user.organization
        )

        if regulatory_updates.exists():
            # Assuming you want to take the first found record's regulatory review
            for policies_record in regulatory_updates:
                regulatory_review = policies_record.regulatory_review
                if regulatory_review:
                    response_data['regulatoryUpdates']['regulatory_review'] = regulatory_review.title

                    # Fetch related regulatory rules
                    rules = RegulatoryRule.objects.filter(regulatory_review=regulatory_review)
                    for rule in rules:
                        response_data['regulatoryUpdates']['rules'].append({
                            'rule_text': rule.rule_text,
                            'rule_order': rule.rule_order
                        })

                    # Add PoliciesAndProcedures related data
                    response_data['regulatoryUpdates'].update({
                        'id': policies_record.id,
                        'policies_procedure_section': policies_record.policies_procedure_section,
                        'work_flow_link': policies_record.work_flow_link,
                        'work_flow_text': policies_record.work_flow_text,
                        'cco_updates_text': policies_record.cco_updates_text,
                        'organization': policies_record.organization.id if policies_record.organization else None,
                        'reviewed_by': policies_record.reviewed_by,
                        'reviewed_date': policies_record.reviewed_date
                    })

        return Response(response_data, status=status.HTTP_200_OK)


class PoliciesAndProceduresFileDeleteView(generics.UpdateAPIView):
    queryset = PoliciesAndProcedures.objects.all()
    serializer_class = PoliciesAndProceduresFileDeleteSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsSuperUserOrCCO]
    swagger_schema = PoliciesAndProceduresSwaggerAutoSchema

    def patch(self, request, *args, **kwargs):
        # Check if the user has the required permissions
        if not (request.user.is_superuser or request.user.role == 'CCO'):
            return Response(
                {"error": "You do not have permission to delete the file."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get the object to be updated
        instance = self.get_object()

        # Update the instance using the serializer
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Return a success response
        return Response(
            {"message": f"File for record ID {kwargs['pk']} successfully deleted."},
            status=status.HTTP_200_OK
        )
