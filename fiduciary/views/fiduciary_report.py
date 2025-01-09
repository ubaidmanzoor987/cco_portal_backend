from rest_framework import viewsets, status
from rest_framework.response import Response
from fiduciary.models import *
from fiduciary.serializers import *
from utils.s3_utils import upload_file_to_s3_folder
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from fiduciary.swagger_schema import FiduciaryReportsSwaggerAutoSchema
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
import pandas as pd
from rest_framework.decorators import action
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

class FiduciaryReportViewSet(viewsets.ModelViewSet):
    queryset = FiduciaryReport.objects.all()
    serializer_class = FiduciaryReportSerializer
    permission_classes = [IsAuthenticated]
    swagger_schema =  FiduciaryReportsSwaggerAutoSchema
    
    @swagger_auto_schema(tags=['Fiduciary Reports'])
    def create(self, request, *args, **kwargs):
        # Pass the request context to the serializer to use the current user
        serializer = self.get_serializer(data=request.data, context={'request': request})
        
        # Extract the is_draft field from the request data
        is_draft = request.data.get('is_draft', False)  # Default to False if not provided

        if serializer.is_valid():
            # Save the report with the specified draft status
            serializer.save(is_draft=is_draft)
            return Response({
                "status": "success",
                "message": "Report created successfully.",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "status": "error",
                "message": "There was an error creating the report.",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        file = request.FILES.get('report_file')
        s3_file_link = instance.s3_file_link  # Default to existing link if no new file

        if file:
            # Upload the new file to S3 and get the link
            file_content = file.read()  # Read the file content as bytes
            content_type = file.content_type
            file_name = file.name
            folder_name = "fiduciary-reports"

            # Call the S3 upload function
            s3_file_data = upload_file_to_s3_folder(file_content, file_name, content_type, folder_name)
            s3_file_link = s3_file_data.get('file_link', {}).get('preview_link')  # Extract the link

        # Serialize the data
        serializer = self.get_serializer(instance, data=request.data, partial=True)

        if serializer.is_valid():
            # Update the report along with the new S3 link if provided
            serializer.save(s3_file_link=s3_file_link)
            return Response({
                "status": "success",
                "message": "Report updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "status": "error",
                "message": "There was an error updating the report.",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

    def get_user_drafts(self, request):
        drafts = FiduciaryReport.objects.filter(user=request.user, is_draft=True)
        serializer = FiduciaryReportSerializer(drafts, many=True)
        return Response({
            "status": "success",
            "data": serializer.data
        })

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            "status": "success",
            "message": "Report retrieved successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
    def destroy(self, request, pk=None):
        """
        Delete a Fiduciary Report by ID.
        """
        try:
            # Fetch the report based on the provided ID
            report = self.get_object()
            report.delete()  # Delete the report
            
            return Response({
                "status": "success",
                "message": "Fiduciary Report deleted successfully."
            }, status=status.HTTP_200_OK) 

        except Exception as e:
            return Response({
                "status": "error",
                "message": "There was an error deleting the report.",
                "errors": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()



class BulkClientUploadViewSet(viewsets.ModelViewSet):
    """
    A ViewSet to handle uploading an Excel/CSV file with multiple clients' data.
    """
    parser_classes = (MultiPartParser, FormParser)  
    swagger_schema = FiduciaryReportsSwaggerAutoSchema
    serializer_class = ClientDataUploadSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Create reports for each client based on uploaded Excel/CSV file.
        """
        file = request.FILES.get('file')
        user = request.user

        if not file:
            return Response({
                "status": "error",
                "message": "File is required for bulk client upload."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Determine if the file is Excel or CSV based on extension
            if file.name.endswith('.xlsx') or file.name.endswith('.xls'):
                client_data = pd.read_excel(file)
            elif file.name.endswith('.csv'):
                client_data = pd.read_csv(file)
            else:
                return Response({
                    "status": "error",
                    "message": "Unsupported file format. Please upload an Excel or CSV file."
                }, status=status.HTTP_400_BAD_REQUEST)

            # List to store the report creation results
            report_creation_results = []
            
            # Iterate through each row in the file and create reports
            for index, row in client_data.iterrows():
                # Extract the client data from the row
                client_details = {
                    "first_name": row.get("First Name"),
                    "last_name": row.get("Last Name"),
                    "client_email": row.get("Client Email Address"),
                    "date_of_birth": row.get("Date of Birth"),
                    "advisor_full_name": row.get("Advisor Full Name"),
                    "date_prepared": row.get("Date Prepared"),
                    "type_of_client": row.get("Type of Client"),
                    "client_risk_tolerance": row.get("Client Risk Tolerance"),
                    "investment_objective": row.get("Investment Objective"),
                    "timeline": row.get("Timeline"),
                    "type_of_plan": row.get("Type of Plan"),
                    "reason_for_rollover": row.get("Reason for Rollover"),
                    "client_goals": row.get("Client Goals"),
                    "advisor_notes": row.get("Advisor Notes")
                }
                
                # Prepare the data in the format required for creating the report
                report_data = {
                    "client_details": client_details,
                    "is_draft": True,
                }

                # Check if a report exists for the client
                existing_report = FiduciaryReport.objects.filter(
                    client_details__first_name=client_details["first_name"],
                    client_details__last_name=client_details["last_name"],
                    user=user
                ).first()

                # Use a transaction to ensure atomicity
                with transaction.atomic():
                    if existing_report:
                        # If an existing report is found, append a message about the existing report
                        report_creation_results.append({
                            "client_email": client_details["client_email"],
                            "status": "info",
                            "message": f"A report already exists for this client: {client_details['first_name']} {client_details['last_name']}."
                        })
                    else:
                        # Create a new report
                        serializer = FiduciaryReportSerializer(data=report_data, context={'request': request})
                        if serializer.is_valid():
                            serializer.save()
                            report_creation_results.append({
                                "client_email": client_details["client_email"],
                                "status": "success",
                                "message": "Report created successfully."
                            })
                        else:
                            report_creation_results.append({
                                "client_email": client_details["client_email"],
                                "status": "error",
                                "message": serializer.errors
                            })

            # Return the results of the report creation
            return Response({
                "status": "success",
                "message": "Client reports processed.",
                "data": report_creation_results
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An error occurred while processing the file: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class ReportResourcesReviewedViewSet(viewsets.ViewSet):
    queryset = ReportResourcesReviewed.objects.all()
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    swagger_schema =  FiduciaryReportsSwaggerAutoSchema
    #serializer_class = DocumentUploadSerializer

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'files', openapi.IN_FORM, description="Upload files", type=openapi.TYPE_FILE, required=True, multiple=True
            )
        ],
        consumes=['multipart/form-data']
    )
    @action(detail=True, methods=['post'], url_path='upload-documents')
    def upload_documents(self, request, pk=None):
        """
        Upload documents and update the document_links field.
        """
        try:
            resources_reviewed = self.get_object()  # Get the specific ReportResourcesReviewed instance
            uploaded_files = request.FILES.getlist('files')  # Get the uploaded files

            if not uploaded_files:
                return Response({
                    "status": "error",
                    "message": "No files provided."
                }, status=status.HTTP_400_BAD_REQUEST)

            document_links = []

            for file in uploaded_files:
                # You would replace this with your actual upload logic to S3
                file_url = self.upload_file_to_s3(file)  # Define this method to handle uploads
                document_links.append(file_url)

            # Update the instance with the new document links
            resources_reviewed.document_links.extend(document_links)
            resources_reviewed.save()

            return Response({
                "status": "success",
                "message": "Documents uploaded successfully.",
                "document_links": resources_reviewed.document_links
            }, status=status.HTTP_200_OK)

        except ReportResourcesReviewed.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Resources reviewed instance not found."
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

