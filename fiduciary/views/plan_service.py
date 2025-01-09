from rest_framework import viewsets, status
from rest_framework.response import Response
from fiduciary.models import *
from fiduciary.serializers import *
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from fiduciary.swagger_schema import  *



class PlanServiceViewSet(viewsets.ModelViewSet):
    queryset = GeneralReportPlanService.objects.all()
    serializer_class =  GeneralPlanServiceAddSerializer
    permission_classes = [IsAuthenticated] 
    swagger_schema =  ReportPlanServicsSwaggerAutoSchema

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            service = serializer.save(created_by=request.user)  
            return Response({
                "status": "success",
                "message": "Plan Service created successfully.",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "status": "error",
                "message": "There was an error creating the Plan Service.",
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
            "message": "Plan Services retrieved successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
    def get_plan_services_by_report(self, request, report_id=None):
        """
        Retrieve all plan services related to a specific report ID.
        """
        # Validate the report ID
        if not report_id:
            return Response({
                "status": "success",
                "message": "Report ID is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        
        # Prepare the response data manually
        response_data = []
        
        # Fetch the plan services related to the given report ID
        plan_services = ReportPlanServices.objects.filter(fiduciaryreport_id=report_id)

        # Check if any plan services exist
        if not plan_services.exists():
            # If no client requirements are found for the report, retrieve all general client requirements
            user = request.user
            
            # Filter general client requirements based on user permissions
            queryset = self.get_queryset().filter(
                Q(created_by=user) | Q(created_by__isnull=True)
            )
            for general_service in queryset:
                plan_services_data={
                    "id": general_service.id,
                    "service_name": general_service.service_name,
                    "current_plan": None,  # No related plan service
                    "recommended_ira": None  # No related plan service
                }
                response_data.append(plan_services_data)
            return Response({
                "status": "success",
                "message": f"No plan services found for report ID {report_id}. Returning plan services",
                "data": {
                "plan_service": response_data,
                "notes": None  
            }
            }, status=status.HTTP_200_OK)
        
       
     
        for plan_service in plan_services:
            plan_services_data = {
                "id": plan_service.general_plan_service.id,
                "service_name": plan_service.general_plan_service.service_name if plan_service.general_plan_service else None,
                "current_plan": plan_service.current_plan,
                "recommended_ira": plan_service.recommended_ira, 
            }
            response_data.append(plan_services_data)

        common_notes = plan_services.first().notes if plan_services.first().notes else None
        return Response({
            "status": "success",
            "message": f"Plan services for report ID {report_id} retrieved successfully.",
            "data": {
                "plan_service": response_data,
                "notes": common_notes  
            }
        }, status=status.HTTP_200_OK)



