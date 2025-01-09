from datetime import datetime

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser

from acr_tool.swagger_schema import *
from acr_tool.models import AWSResourceFile
from acr_tool.permissions import IsSuperUserOrCCO
from acr_tool.serializers import AWSResourceFileSerializer


class AWSResourceFileViewSet(viewsets.ModelViewSet):
    queryset = AWSResourceFile.objects.all()
    serializer_class = AWSResourceFileSerializer
    authentication_classes = [TokenAuthentication]
    parser_classes = (MultiPartParser, FormParser)
    swagger_schema = AWSResourceFileSwaggerAutoSchema

    def get_permissions(self):
        if self.action in ['create']:
            # Apply custom permission only for the create action
            permission_classes = [IsAuthenticated, IsSuperUserOrCCO]
        else:
            # Allow any authenticated user for other actions
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def get_queryset(self):
        current_year = datetime.now().year
        return AWSResourceFile.objects.filter(created_at__year=current_year)

    def create(self, request, *args, **kwargs):
        acr_tab = request.data.get('acr_tab')
        current_year = datetime.now().year

        # Check if a record already exists for the given acr_tab and current year
        existing_record = AWSResourceFile.objects.filter(acr_tab=acr_tab, created_at__year=current_year).first()

        if existing_record:
            serializer = self.get_serializer(existing_record, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response({"message": "File successfully updated."}, status=status.HTTP_200_OK)
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(created_by=request.user)
            return Response({"message": "File successfully uploaded."}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def current_year_records(self, request):
        """Custom endpoint to get all records for the current year."""
        current_year = datetime.now().year
        records = AWSResourceFile.objects.filter(created_at__year=current_year)

        # Serialize the records
        serializer = self.get_serializer(records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
