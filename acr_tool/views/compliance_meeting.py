from datetime import datetime
from django.db.models import Prefetch

from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from acr_tool.models import *
from acr_tool.permissions import *
from acr_tool.serializers import *
from acr_tool.swagger_schema import *


class ComplianceMeetingInstructionsViewSet(viewsets.ModelViewSet):
    queryset = ComplianceMeetingInstructions.objects.all()
    serializer_class = ComplianceMeetingInstructionsSerializer
    authentication_classes = [TokenAuthentication]
    swagger_schema = ComplianceMeetingInstructionsSwaggerAutoSchema

    def get_permissions(self):
        # Allow both superuser for create, update, destroy actions and CCO for retrieve actions
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsSuperUser]
        else:  # For retrieve and list actions
            permission_classes = [IsSuperUserOrCCO]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        # Ensure that only one instance is returned
        return ComplianceMeetingInstructions.objects.all()

    def perform_create(self, serializer):
        if ComplianceMeetingInstructions.objects.exists():
            raise serializers.ValidationError({"detail": "Only one record is allowed."})
        else:
            serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save()


class TopicViewSet(viewsets.ModelViewSet):
    queryset = ComplianceMeetingTopic.objects.all()
    serializer_class = TopicSerializer
    authentication_classes = [TokenAuthentication]
    swagger_schema = ComplianceMeetingTopicSwaggerAutoSchema

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated(), IsSuperUserOrCCO()]
        return [IsAuthenticated(), IsSuperUser()]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or (hasattr(user, 'role') and user.role == 'CCO'):
            return ComplianceMeetingTopic.objects.all()
        return ComplianceMeetingTopic.objects.none()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        topic = serializer.save()
        return Response({"status": "success", 'message': 'Topic created successfully.'},
                        status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        topic = serializer.save()
        return Response({"status": "success", 'message': 'Topic updated successfully.'},
                        status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"status": "success", 'message': 'Topic deleted successfully.'},
                        status=status.HTTP_204_NO_CONTENT)


class ComplianceMeetingTopicViewSet(viewsets.ModelViewSet):
    queryset = ComplianceMeetingTopic.objects.all()
    serializer_class = ComplianceMeetingTopicSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated & (IsSuperUser | IsSuperUserOrCCO)]
    swagger_schema = ComplianceMeetingTopicSwaggerAutoSchema

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(created_by=user)


class ComplianceMeetingViewSet(viewsets.ModelViewSet):
    queryset = ComplianceMeeting.objects.all()
    serializer_class = ComplianceMeetingSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsSuperUserOrCCO]
    swagger_schema = ComplianceMeetingSwaggerAutoSchema

    def get_queryset(self):
        user = self.request.user
        current_year = datetime.now().year

        # Check if the user is authenticated
        if user.is_authenticated:
            # Superusers and CCO users can view all records
            if user.is_superuser or (hasattr(user, 'role') and user.role == 'CCO'):
                return ComplianceMeeting.objects.all()

            # For other authenticated users, return records related to their organization and for the current year
            if hasattr(user, 'organization'):
                return ComplianceMeeting.objects.filter(
                    organization=user.organization,
                    created_at__year=current_year
                )

        # If the user is not authenticated or does not have an organization, return an empty queryset
        return ComplianceMeeting.objects.none()

    def perform_create(self, serializer):
        current_year = datetime.now().year

        # Check if a ComplianceMeeting record already exists for the current year
        existing_record = ComplianceMeeting.objects.filter(
            created_at__year=current_year,
            organization=self._get_organization()
        ).first()

        if existing_record:
            raise ValidationError(f"A Compliance Meeting record already exists for the year {current_year}.")

        # Modify the incoming data to handle topic_id instead of topic
        compliance_meeting_data = self.request.data.get('compliance_meeting_data', [])
        for data in compliance_meeting_data:
            data['topic'] = data.pop('topic_id')  # Replace topic_id with topic

        # Save the new record
        meeting = serializer.save(created_by=self.request.user, organization=self._get_organization())

        # Return a custom success response
        return Response(
            {"message": "Compliance Meeting created successfully.", "id": meeting.id},
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        # Overriding the default update method to return a custom response
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # Modify the incoming data to handle topic_id instead of topic
        compliance_meeting_data = request.data.get('compliance_meeting_data', [])
        for data in compliance_meeting_data:
            data['topic'] = data.pop('topic_id')  # Replace topic_id with topic

        meeting = serializer.save(created_by=self.request.user, organization=self._get_organization())

        # Return a custom success response
        return Response(
            {"message": f"Compliance Meeting with ID {meeting.id} updated successfully."},
            status=status.HTTP_200_OK
        )

    def _get_organization(self):
        if self.request.user.is_superuser:
            return None
        return self.request.user.organization

    @action(detail=False, methods=['get'])
    def sample_payload(self, request):
        """
        Returns a sample dynamic payload as a response.
        """
        sample_payload = {
            "compliance_meeting_data": [
                {
                    "topic": 1,
                    "sample_questions": [
                        1, 2
                    ],
                    "custom_questions": [
                        "string 1"
                    ],
                    "comment": "string"
                },
                {
                    "topic": 2,
                    "sample_questions": [
                        3, 4, 5
                    ],
                    "custom_questions": [
                        "string 2", "string 3"
                    ],
                    "comment": "string"
                }
            ]
        }
        return Response(sample_payload)


class ComplianceMeetingCurrentYearViewSet(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsSuperUserOrCCO]
    swagger_schema = ComplianceMeetingSwaggerAutoSchema

    @action(detail=False, methods=['get'], url_path='current_year')
    def get_current_year_compliance_meeting(self, request):
        """
        Get the ComplianceMeeting record for the current year if it exists.
        If no record exists, create a "dummy" ComplianceMeeting record and return it.
        """
        current_year = datetime.now().year
        user = request.user

        # Check if a record for the current year exists
        existing_record = ComplianceMeeting.objects.filter(created_at__year=current_year,
                                                           organization=user.organization).first()

        if existing_record:
            serializer = ComplianceMeetingDetailSerializer(existing_record)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Create a "dummy" ComplianceMeeting record if none exists
        dummy_meeting = ComplianceMeeting.objects.create(
            created_by=user,
            organization=self._get_organization(),
        )

        # Save the dummy meeting (topics and sample_questions remain empty)
        dummy_meeting.save()

        # Serialize the newly created dummy record
        serializer = ComplianceMeetingDetailSerializer(dummy_meeting)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _get_organization(self):
        user = self.request.user
        if user.is_superuser:
            return None
        return user.organization
