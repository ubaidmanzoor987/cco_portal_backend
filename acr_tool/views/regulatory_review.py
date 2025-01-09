from datetime import datetime

from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, viewsets, serializers
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser

from acr_tool.swagger_schema import *
from acr_tool.models import SecRuleLinks, RegulatoryReview, RegulatoryReviewInstructions
from acr_tool.permissions import IsSuperUser, IsSuperUserOrCCO
from acr_tool.serializers import (
    SecRuleLinksSerializer, RegulatoryReviewSerializer, RegulatoryReviewInstructionsSerializer
)


class SecRuleLinksViewSet(viewsets.ModelViewSet):
    queryset = SecRuleLinks.objects.all()
    serializer_class = SecRuleLinksSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    swagger_schema = SecRuleLinksSwaggerAutoSchema

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperUser()]
        elif self.action in ['list', 'retrieve']:
            return [IsSuperUserOrCCO()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        # Check if user is a superuser
        if not request.user.is_superuser:
            return Response(
                {"detail": "Current logged-in user does not have permission to create a new record."},
                status=status.HTTP_403_FORBIDDEN
            )

        rule_name = request.data.get('rule_name')
        # Prevent duplicate entries for rule_name
        if SecRuleLinks.objects.filter(rule_name=rule_name).exists():
            return Response(
                {"detail": f"A record for '{rule_name}' already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        # Check if user is a superuser
        if not request.user.is_superuser:
            return Response(
                {"detail": "Only superusers can update records."},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().update(request, *args, **kwargs)

    def get_by_section(self, request, section):
        """Retrieve all rule links for a given section."""
        # Check if the provided section is valid
        valid_sections = [SecRuleLinks.FINAL_RULES,
                          SecRuleLinks.ENFORCEMENT_ACTIONS,
                          SecRuleLinks.RISK_ALERTS,
                          SecRuleLinks.PRESS_RELEASES]

        if section not in valid_sections:
            return Response(
                {"detail": f"Invalid section provided: '{section}'. Valid options are: {', '.join(valid_sections)}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Filter records by section and retrieve rule links
        records = SecRuleLinks.objects.filter(rule_name=section)
        if not records.exists():
            return Response(
                {"detail": f"No records found for section '{section}'."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Prepare the response data
        rule_links_data = [{"rule_name": record.rule_name, "rule_links": record.rule_links} for record in records]
        return Response(rule_links_data, status=status.HTTP_200_OK)


class RegulatoryReviewViewSet(viewsets.ModelViewSet):
    queryset = RegulatoryReview.objects.all()
    serializer_class = RegulatoryReviewSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    swagger_schema = RegulatoryReviewSwaggerAutoSchema

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperUserOrCCO()]
        elif self.action in ['list', 'retrieve', 'get_by_year']:
            return [IsSuperUserOrCCO()]
        return super().get_permissions()

    def get_queryset(self):
        # Get the current year
        current_year = datetime.utcnow().year

        # Filter records by the current user's organization and the current year
        queryset = RegulatoryReview.objects.filter(
            organization=self.request.user.organization,
            created_at__year=current_year
        )

        return queryset

    def perform_create(self, serializer):
        section = serializer.validated_data.get('section')
        organization = self.request.user.organization
        current_year = datetime.utcnow().year

        # Ensure only one record per section, organization, and year
        if RegulatoryReview.objects.filter(section=section, organization=organization,
                                           created_at__year=current_year).exists():
            raise ValidationError({
                "detail": f"Only one record per section per organization per year is allowed. A record already exists for {section} in {current_year} for your organization."
            })

        # Save the regulatory review instance
        serializer.save(created_by=self.request.user, organization=organization)

    def create(self, request, *args, **kwargs):
        if not request.user.is_superuser and not request.user.role == 'CCO':
            return Response({"detail": "Current logged in user does not have permission to create a new record."},
                            status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not request.user.is_superuser and not request.user.role == 'CCO':
            return Response({"detail": "Only superusers or users with the CCO role can update records."},
                            status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not request.user.is_superuser and not request.user.role == 'CCO':
            return Response({"detail": "Only superusers or users with the CCO role can update records."},
                            status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response({"detail": "Only superusers can delete records."}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path=r'by-year/(?P<year>\d{4})')
    def get_by_year(self, request, year=None):
        if not request.user.is_superuser and not request.user.role == 'CCO':
            return Response({"detail": "Only superusers or users with the CCO role can retrieve records by year."},
                            status=status.HTTP_403_FORBIDDEN)

        try:
            year = int(year)
        except ValueError:
            return Response({"detail": "Year query parameter must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        # Get the current user's organization
        organization = request.user.organization

        # Get the regulatory reviews for the specified year and organization
        results = {}
        for section, _ in SecRuleLinks.SECTION_CHOICES:
            results[section] = RegulatoryReview.objects.filter(
                section=section,
                created_at__year=year,
                organization=organization
            )

        # Serialize and return the results
        serializer = RegulatoryReviewSerializer([item for sublist in results.values() for item in sublist], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RegulatoryReviewInstructionsViewSet(viewsets.ModelViewSet):
    queryset = RegulatoryReviewInstructions.objects.all()
    serializer_class = RegulatoryReviewInstructionsSerializer
    authentication_classes = [TokenAuthentication]
    swagger_schema = RegulatoryReviewInstructionsSwaggerAutoSchema

    def get_permissions(self):
        # Allow both superuser for create, update, destroy actions and CCO for retrieve actions
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsSuperUser]
        else:  # For retrieve and list actions
            permission_classes = [IsSuperUserOrCCO]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        # Ensure that only one instance is returned
        return RegulatoryReviewInstructions.objects.all()

    def perform_create(self, serializer):
        # Check if a record already exists
        if RegulatoryReviewInstructions.objects.exists():
            # If a record exists, raise an error response
            raise serializers.ValidationError({"detail": "Only one record is allowed."})
        else:
            serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save()
