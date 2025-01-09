import os
import base64
from docx import Document
from docx.shared import Pt
from docx.shared import Inches
from pdf2docx import Converter

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from organization.models import Organization

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser

from acr_tool.models import *
from acr_tool.serializers import *
from acr_tool.permissions import *
from acr_tool.swagger_schema import *


class AnnualReportInstructionsViewSet(viewsets.ModelViewSet):
    queryset = AnnualReportInstructions.objects.all()
    serializer_class = AnnualReportInstructionsSerializer
    authentication_classes = [TokenAuthentication]
    swagger_schema = AnnualReportInstructionsSwaggerAutoSchema

    def get_permissions(self):
        # Allow both superuser for create, update, destroy actions and CCO for retrieve actions
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsSuperUser]
        else:  # For retrieve and list actions
            permission_classes = [IsSuperUserOrCCO]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        return AnnualReportInstructions.objects.all()  # Allow retrieval of all instances

    def perform_create(self, serializer):
        # Check if a record already exists
        if AnnualReportInstructions.objects.exists():
            # If a record exists, raise an error response
            raise serializers.ValidationError({"detail": "Only one record is allowed."})
        else:
            serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save()


class ACRInstructionsViewSet(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsSuperUserOrCCO]
    swagger_schema = ARCAllInstructionsSwaggerAutoSchema

    def list(self, request):
        response_data = {}

        # Retrieve the first record from each model
        regulatory_review_instructions = RegulatoryReviewInstructions.objects.first()
        risk_assessment_instructions = RiskAssessmentInstructions.objects.first()
        policies_and_procedures_instructions = PoliciesAndProceduresInstructions.objects.first()
        procedure_review_instructions = ProcedureReviewInstructions.objects.first()
        compliance_meeting_instructions = ComplianceMeetingInstructions.objects.first()
        annual_report_instructions = AnnualReportInstructions.objects.first()

        # Build the response data structure
        if regulatory_review_instructions:
            response_data['regulatory_review'] = {
                'instructions': regulatory_review_instructions.instructions,
                'example': regulatory_review_instructions.example
            }

        if risk_assessment_instructions:
            response_data['risk_assessment'] = {
                'instructions': risk_assessment_instructions.instructions
            }

        if policies_and_procedures_instructions:
            response_data['policies_and_procedures'] = {
                'instructions': policies_and_procedures_instructions.instructions,
                'overview': policies_and_procedures_instructions.overview
            }

        if procedure_review_instructions:
            response_data['procedure_review'] = {
                'instructions': procedure_review_instructions.instructions,
                'overview': procedure_review_instructions.overview
            }

        if compliance_meeting_instructions:
            response_data['compliance_meeting'] = {
                'instructions': compliance_meeting_instructions.instructions,
                'overview': compliance_meeting_instructions.overview
            }

        if annual_report_instructions:
            response_data['annual_report'] = {
                'instructions': annual_report_instructions.instructions,
                'background': annual_report_instructions.background,
                'overview_crp': annual_report_instructions.overview_crp,
                'regulatory_developments': annual_report_instructions.regulatory_developments,
                'work_completed': annual_report_instructions.work_completed,
                'test_conducted': annual_report_instructions.test_conducted,
                'conclusion': annual_report_instructions.conclusion
            }

        return Response(response_data)


class AnnualReportViewSet(viewsets.ModelViewSet):
    queryset = AnnualReport.objects.all()
    serializer_class = AnnualReportSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    swagger_schema = AnnualReportSwaggerAutoSchema

    def get_permissions(self):
        """Set the appropriate permissions for the actions."""
        if self.action == 'partial_update':
            self.permission_classes = [IsSuperUserOrCCO]
        else:
            self.permission_classes = [IsAuthenticated]
        return super(AnnualReportViewSet, self).get_permissions()

    def get_queryset(self):
        """Filter queryset for the current year records."""
        current_year = timezone.now().year
        user = self.request.user
        return AnnualReport.objects.filter(created_at__year=current_year, organization=user.organization)

    def list(self, request, *args, **kwargs):
        """Override the list to ensure a record exists for the current year."""
        current_year = timezone.now().year

        organization = None if request.user.is_superuser else request.user.organization
        # Check if a report exists for the current year
        report = AnnualReport.objects.filter(created_at__year=current_year, organization=organization).first()

        # If no report exists, create a dummy record with default field values
        if not report:
            report = AnnualReport.objects.create(
                organization=organization,
                created_by=request.user,
                # Set default values for the new report
                cover_page="<p><span style=\"white-space:pre-wrap;\"><strong>Top Advisors, LLC</strong></span><br><span style=\"white-space:pre-wrap;\"><strong>2024</strong></span></p><p><span style=\"white-space:pre-wrap;\"><strong>Annual Compliance Review Report</strong></span></p><p><span style=\"white-space:pre-wrap;\"><span style=\"white-space:pre-wrap;\">Report Created by: Ted Danson </span></span></p><p><span style=\"white-space:pre-wrap;\"><span style=\"white-space:pre-wrap;\">February 24, 2025</span><br></span></p>",
                introduction_page="<p><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><strong>Date : </strong>February 2, 20241</span></p><p><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"white-space:pre-wrap;\"><strong>To:</strong> Thomas Evans, CEO &amp; Board Chair</span></span></p><p><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"white-space:pre-wrap;\"><span style=\"white-space:pre-wrap;\"><strong>From: </strong>Bryan Hill, Chief Compliance Officer </span></span></span></p><p><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"white-space:pre-wrap;\"><span style=\"white-space:pre-wrap;\"><span style=\"white-space:pre-wrap;\"><strong>Re: </strong>2023 Annual Compliance Program Review</span></span></span></span></p><p><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\">Rule 2069(4)-7 the investor Advisor's Act requires each registered investment advisor to perform an annual<br>review of their compliance program. Include in the annual report is a comprehensive review of current policies<br>and procedures and a formal risk assessment to identify the adequacy and effectiveness of their<br>implementation. This is the formal report of all compliance activities that look place in 2023.  </span></p><p><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\">The compliance report is broken down into the following sections: </span></span></p><p><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><strong>1.Background:</strong></span></span></p><p><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\">A brief description of the firm and its main lines of business, including its Assets under management as of December 2023. </span></span></span></p><p><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><strong>2.</strong><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><strong>Overview of compliance review process:</strong></span></span></span></span></p><p><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\">An overview of how the firm's compliance program is administered. Who conducted the review , when it was conducted, the period covered and the scope of the program review. </span></span></span></span></span></p><p><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><strong>3.Regulatory developments &amp; firm business model</strong></span></span></span></span></span></span></p><p><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\">A look into any new SEC regulatory updates that apply as well as adjustment to the RIA business model and how a new SEC regulation affects this new business offering. </span></span></span></span></span></span></span></p><p><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><strong>4.Work Completed in 2023</strong></span></span></span></span></span></span></span></span></p><p><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\">1.A formal review of the firm's policies &amp; procedures.<br>2.A detailed look at the firm's compliance calendar, compliance program annual procedure review &amp; testing conducted.<br>3.The completed risk inventory.<br>4.The annual compliance meeting.</span></span></span></span></span></span></span></span></span></p><p><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><strong>5.Tests conducted, recommendations for improvement &amp; work to be completed in 2024. </strong></span></span></span></span></span></span></span></span></span></span></p><p><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\"><span style=\"\\&quot;\\\\&quot;white-space:pre-wrap;\\\\&quot;\\&quot;\">Testing out comes and areas to be adjusted in 2024 based on the testing result</span></span></span></span></span></span></span></span></span></span></span><br></p>"
            )

        serializer = self.get_serializer(report)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'blank_page': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'page_order': openapi.Schema(type=openapi.TYPE_STRING, example='1'),
                            'page_text': openapi.Schema(type=openapi.TYPE_STRING, example='string1'),
                        },
                        required=['page_order', 'page_text']
                    ),
                ),
                'cover_page': openapi.Schema(type=openapi.TYPE_STRING, example='Cover Page Text'),
                'introduction_page': openapi.Schema(type=openapi.TYPE_STRING, example='Introduction Text'),
                'background_firm_narrative': openapi.Schema(type=openapi.TYPE_STRING, example='Background Narrative'),
                'overview_compliance_review_process': openapi.Schema(type=openapi.TYPE_STRING,
                                                                     example='Overview Process'),
                'test_recommendation_next_year': openapi.Schema(type=openapi.TYPE_STRING, example='Recommendation'),
                'conclusion': openapi.Schema(type=openapi.TYPE_STRING, example='Conclusion Text'),
            },
            required=[]
        )
    )
    def partial_update(self, request, *args, **kwargs):
        """Override partial update to handle specific permission and field restrictions."""
        instance = self.get_object()
        data = request.data.copy()

        # Ensure blank_page is a list of dictionaries and handle it
        if 'blank_page' in data:
            for page in data['blank_page']:
                if 'page_order' in page:
                    instance.blank_page.append({
                        "page_order": page['page_order'],
                        "page_text": page.get('page_text', "")
                    })
                else:
                    return Response({'blank_page': "Each item must contain 'page_order'."},
                                    status=status.HTTP_400_BAD_REQUEST)

        # Prevent 'organization', 'created_by', and 'created_at' from being updated
        data.pop('organization', None)
        data.pop('created_by', None)
        data.pop('created_at', None)

        # Proceed with the partial update
        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data, status=status.HTTP_200_OK)


class ConvertPDFToWordViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperUserOrCCO]
    serializer_class = PDFToWordSerializer
    authentication_classes = [TokenAuthentication]
    parser_classes = (MultiPartParser, FormParser)
    swagger_schema = ConvertPDFToWordSwaggerAutoSchema

    def create(self, request, *args, **kwargs):
        # Deserialize the request data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get the uploaded PDF file
        pdf_file = serializer.validated_data['pdf_file']
        pdf_file_name = pdf_file.name

        # Save the PDF file temporarily
        pdf_file_path = default_storage.save(pdf_file_name, ContentFile(pdf_file.read()))

        # Get the full path of the saved file
        full_pdf_file_path = default_storage.path(pdf_file_path)

        try:
            # Convert PDF to Word
            docx_file_name = pdf_file_name.replace('.pdf', '.docx')
            docx_file_path = os.path.join('/tmp', docx_file_name)  # Using /tmp for temporary files
            converter = Converter(full_pdf_file_path)  # Use the full path here
            converter.convert(docx_file_path, start=0, end=None)  # Convert entire document
            converter.close()

            # Now, we need to ensure that the DOCX file is in A4 size
            # Create a new Document with A4 dimensions
            doc = Document(docx_file_path)

            # Define A4 dimensions in inches
            A4_WIDTH = 8.27  # A4 width in inches
            A4_HEIGHT = 11.69  # A4 height in inches

            # Set the page size to A4
            section = doc.sections[0]
            section.page_width = Inches(A4_WIDTH)
            section.page_height = Inches(A4_HEIGHT)

            # Save the updated document
            doc.save(docx_file_path)

            # Read the DOCX file and encode it to base64
            with open(docx_file_path, "rb") as docx_file:
                docx_file_content = docx_file.read()
                base64_encoded_data = base64.b64encode(docx_file_content).decode('utf-8')

            # Clean up the temporary files
            os.remove(full_pdf_file_path)
            os.remove(docx_file_path)

            # Return the base64 encoded string in the response
            return Response({"word_file_base64": base64_encoded_data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
