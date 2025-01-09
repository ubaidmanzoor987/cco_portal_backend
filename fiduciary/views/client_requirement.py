from rest_framework import viewsets, status
from rest_framework.response import Response
from fiduciary.models import *
from fiduciary.serializers import *
from rest_framework.permissions import IsAuthenticated
from fiduciary.swagger_schema import *
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema



class ClientRequirementsViewSet(viewsets.ModelViewSet):
    queryset = ReportGeneralClientRequirement.objects.all()
    serializer_class = GeneralClientRequirementAddSerializer
    permission_classes = [IsAuthenticated]
    swagger_schema =  ReportClientRequirementSwaggerAutoSchema

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            requirement = serializer.save(created_by=request.user)  
            return Response({
                "status": "success",
                "message": "Client requirement created successfully.",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            "status": "error",
            "message": "There was an error creating the client requirement.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        user = request.user

        # Check if user has CCO role
        if user.role == 'CCO': 
            queryset = self.get_queryset()  # CCO sees all records
        else:
            # Other users see only records created by them or those without a creator
            queryset = self.get_queryset().filter(
                Q(created_by=user) | Q(created_by__isnull=True)
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "status": "success",
            "message": "Client Requirements retrieved successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
    
    def get_client_requirements_by_report(self, request, report_id=None):
        """
        Retrieve all client requirements related to a specific report ID.
        """
        # Validate the report ID
        if not report_id:
            return Response({
                "status": "error",
                "message": "Report ID is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Prepare the response data manually
        response_data = []
        
        # Fetch the client requirements related to the given report ID
        client_requirements = ReportClientRequirements.objects.filter(fiduciaryreport_id=report_id)

        # Check if any client requirements exist
        if not client_requirements.exists() or not any(req.general_requirement for req in client_requirements):
           
            # Filter general client requirements based on user permissions
            queryset = self.get_queryset().filter(created_by__isnull=True)
            
            # Prepare the response data for general client requirements
            for general_requirement in queryset:
                response_data.append({
                    "id": general_requirement.id,
                    "requirement_text": general_requirement.requirement_text,
                    "status": None,  # No related client requirement
                })

            return Response({
                "status": "success",
                "message": f"No client requirements found for report ID {report_id}. Returning general client requirements.",
                "data": {
                    "requirements": response_data,
                    "notes": None  # General notes can be set here if applicable
                }
            }, status=status.HTTP_200_OK)

        # If client requirements exist, format the data accordingly
        common_notes = client_requirements.first().notes if client_requirements.first().notes else None

        for requirement in client_requirements:
            requirement_data = {
                "id": requirement.general_requirement.id,
                "requirement_text": requirement.general_requirement.requirement_text if requirement.general_requirement else None,
                "status": requirement.status,
            }
            response_data.append(requirement_data)

        return Response({
            "status": "success",
            "message": f"Client requirements for report ID {report_id} retrieved successfully.",
            "data": {
                "requirements": response_data,
                "notes": common_notes  
            }
        }, status=status.HTTP_200_OK)