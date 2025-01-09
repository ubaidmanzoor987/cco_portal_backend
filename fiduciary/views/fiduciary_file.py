from rest_framework import viewsets, status
from rest_framework.response import Response
from fiduciary.models import *
from fiduciary.serializers import *
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from utils.s3_utils import upload_file_to_s3_folder
from rest_framework.permissions import IsAuthenticated
from fiduciary.swagger_schema import *
from pdf2docx import Converter  
import os
import io
import requests 
from django.http import HttpResponse
import tempfile
import base64

class FiduciaryReportFileViewSet(viewsets.ModelViewSet):
    queryset = FiduciaryReport.objects.all()  
    serializer_class = UpdateReportFileDetailsSerializer
    permission_classes = [IsAuthenticated]
    swagger_schema =  FiduciaryReportFileSwaggerAutoSchema

    @action(detail=True, methods=['put'], url_path='update-report-details')
    def update_report_file_details(self, request, pk=None):
        """
        Update cover page, introduction page, and disclosures for a Fiduciary Report.
        """
        try:
            # Fetch the report based on the provided ID
            report = self.get_object()

            # Use the UpdateReportDetailsSerializer to validate and update the report
            serializer = UpdateReportFileDetailsSerializer(report, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save() 
                return Response({
                    "status": "success",
                    "message": "Report details updated successfully.",
                    "data": serializer.data  # Return only the updated fields
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "status": "error",
                    "message": "There was an error updating the report details.",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "status": "error",
                "message": "There was an error updating the report details.",
                "errors": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    
    @action(detail=True, methods=['get'])
    def get_report_file_details(self, request, pk=None):
        """
        Retrieve cover page, introduction page, and disclosures for a Fiduciary Report.
        """
        try:
            # Fetch the report based on the provided ID
            report = self.get_object()

            # Serialize the report using UpdateReportFileDetailsSerializer
            serializer = UpdateReportFileDetailsSerializer(report)

            return Response({
                "status": "success",
                "message": "Report file details retrieved successfully.",
                "data": serializer.data  # Return the fields (cover_page, introduction_page, disclosures)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "message": "There was an error retrieving the report details.",
                "errors": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class FiduciaryFileUploadViewSet(viewsets.ModelViewSet):
    serializer_class = FiduciaryFileUploadSerializer
    parser_classes = (MultiPartParser, FormParser) 
    permission_classes = [IsAuthenticated]
    swagger_schema =  FiduciaryReportFileSwaggerAutoSchema
    
    def create(self, request, report_id=None):
        # Validate that the report exists
        try:
            fiduciary_report = FiduciaryReport.objects.get(id=report_id)
        except FiduciaryReport.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Fiduciary Report not found."
            }, status=status.HTTP_404_NOT_FOUND)

        # Use the file upload serializer
        serializer = FiduciaryFileUploadSerializer(data=request.data)
        if serializer.is_valid():
            # Extract file and upload to S3
            file = serializer.validated_data['file']
            file_content = file.read()
            file_name = file.name
            content_type = file.content_type

            # Upload file to S3 and get the link
            resource_s3_file_link = upload_file_to_s3_folder(file_content, file_name, content_type, 'fiduciary_reports')

            # Save the S3 link in the FiduciaryReport
            fiduciary_report.s3_file_link = resource_s3_file_link['file_link']['preview_link']
            fiduciary_report.save()

            return Response({
                "status": "success",
                "message": "File uploaded successfully.",
                "data": {
                    "file_link": fiduciary_report.s3_file_link
                }
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "status": "error",
                "message": "There was an error uploading the file.",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)


class FiduciaryReportReviewUpdateView(viewsets.ModelViewSet):
    queryset = FiduciaryReport.objects.all()
    serializer_class = FiduciaryReportFileUpdateSerializer
    permission_classes = [IsAuthenticated]
    swagger_schema =  FiduciaryReportFileSwaggerAutoSchema

    @action(detail=True, methods=['put'])
    def update_report_review(self, request, pk=None):
        try:
            fiduciary_report = FiduciaryReport.objects.get(id=pk)

            serializer = FiduciaryReportFileUpdateSerializer(fiduciary_report, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "status": "success",
                    "message": "Review updated successfully.",
                    "review": serializer.data
                }, status=status.HTTP_200_OK)

            return Response({
                "status": "error",
                "message": "There was an error updating the review.",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except FiduciaryReport.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Fiduciary Report not found."
            }, status=status.HTTP_404_NOT_FOUND)
        


class ReportDashboardViewSet(viewsets.ModelViewSet):
    serializer_class = ReportDashboardSerializer
    permission_classes = [IsAuthenticated]
    swagger_schema = FiduciaryDashboardSwaggerAutoSchema

    def get_queryset(self):
        """
        Override get_queryset to return reports based on user role and is_draft status.
        """
        user = self.request.user

        # Filter only reports with is_draft=False
        if user.role == 'CCO':  
            # CCO can see all finalized reports
            return FiduciaryReport.objects.filter(is_draft=False)
        
        # Regular users only see their own finalized reports
        return FiduciaryReport.objects.filter(user=user, is_draft=False)

    def list(self, request, *args, **kwargs):
        """
        Override list to provide a response based on the queryset filtered by role and draft status.
        """
        reports = self.get_queryset()
        serializer = ReportDashboardSerializer(reports, many=True)

        return Response({
            "status": "success",
            "message": "Report dashboard data retrieved successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


class PDFToWordConversionViewSet(viewsets.ViewSet):
    """
    A viewset to handle the PDF to Word conversion for Fiduciary reports.
    """
    
    swagger_schema =  FiduciaryReportFileSwaggerAutoSchema

    @action(detail=True, methods=['get'])
    def convert_to_word(self, request, report_id=None):
        """
        Convert the stored PDF file of the report to Word format and return as a base64-encoded string.
        """
        try:
            # Retrieve the report by ID
            report = FiduciaryReport.objects.get(id=report_id)

            # Get the S3 link for the PDF file
            pdf_file_url = report.s3_file_link
            if not pdf_file_url:
                return Response({
                    "status": "error",
                    "message": "PDF file not found."
                }, status=status.HTTP_404_NOT_FOUND)

            # Download the PDF content from the S3 URL
            pdf_file_content = self.get_pdf_content_from_url(pdf_file_url)

            if pdf_file_content is None:
                return Response({
                    "status": "error",
                    "message": "Unable to retrieve the PDF file from S3."
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Convert the PDF to Word dynamically
            word_file_content = self.convert_pdf_to_word(pdf_file_content)

            # Encode the Word file content to base64
            word_file_base64 = base64.b64encode(word_file_content).decode('utf-8')

            # Create the response with base64-encoded Word file content
            return Response({
                "status": "success",
                "message": "PDF successfully converted to Word.",
                "data": {
                    "file_name": f"report_{report.id}.docx",
                    "file_content_base64": word_file_base64
                }
            }, status=status.HTTP_200_OK)

        except FiduciaryReport.DoesNotExist:
            return Response({
                "status": "error",
                "message": f"Report with ID {report_id} not found."
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_pdf_content_from_url(self, pdf_url):
        """
        Retrieve the PDF content from the provided S3 link.
        """
        try:
            # Make an HTTP GET request to download the PDF file
            response = requests.get(pdf_url)
            if response.status_code == 200:
                return response.content  # Return the PDF content as bytes
            else:
                return None
        except Exception as e:
            return None

    def convert_pdf_to_word(self, pdf_content):
        """
        Convert PDF content to Word format using a PDF-to-Word conversion library.
        """
        # Write the PDF content to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            temp_pdf.write(pdf_content)
            temp_pdf_path = temp_pdf.name

        # Create a temporary file for the Word document
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_word:
            temp_word_path = temp_word.name

        # Convert PDF to Word using the pdf2docx library
        converter = Converter(temp_pdf_path)
        converter.convert(temp_word_path)  # Convert and save to the temporary Word file
        converter.close()

        # Read the generated Word file content
        with open(temp_word_path, "rb") as word_file:
            word_file_content = word_file.read()

        # Clean up the temporary files
        temp_pdf.close()
        temp_word.close()

        return word_file_content