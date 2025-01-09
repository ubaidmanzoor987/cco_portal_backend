from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser

from acr_tool.permissions import *
from acr_tool.swagger_schema import *
from acr_tool.models import ProcedureReview
from acr_tool.serializers.procedure_review import *


class ProcedureReviewInstructionsViewSet(viewsets.ModelViewSet):
    queryset = ProcedureReviewInstructions.objects.all()
    serializer_class = ProcedureReviewInstructionsSerializer
    authentication_classes = [TokenAuthentication]
    swagger_schema = ProcedureReviewInstructionsSwaggerAutoSchema

    def get_permissions(self):
        # Allow both superuser for create, update, destroy actions and CCO for retrieve actions
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsSuperUser]
        else:  # For retrieve and list actions
            permission_classes = [IsSuperUserOrCCO]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        # Ensure that only one instance is returned
        return ProcedureReviewInstructions.objects.all()

    def perform_create(self, serializer):
        # Check if a record already exists
        if ProcedureReviewInstructions.objects.exists():
            raise serializers.ValidationError({"detail": "Only one record is allowed."})
        else:
            serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save()


class ProcedureReviewViewSet(viewsets.ModelViewSet):
    queryset = ProcedureReview.objects.all()
    serializer_class = ProcedureReviewSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    swagger_schema = ProcedureReviewSwaggerAutoSchema

    def get_queryset(self):
        user = self.request.user
        current_year = datetime.now().year
        if user.is_superuser:
            return ProcedureReview.objects.filter(created_at__year=current_year)
        elif hasattr(user, 'role') and user.role == 'CCO':
            return ProcedureReview.objects.filter(
                created_at__year=current_year, organization=user.organization
            )
        else:
            return ProcedureReview.objects.none()

    def list(self, request, *args, **kwargs):
        """
        Override the list method to return the ProcedureReview record for the current year
        and the logged-in user's organization. If none exists, create a new record.
        """
        user = request.user
        current_year = datetime.now().year

        # Check if there's an existing record for the current year and user's organization
        existing_record = self.get_queryset().filter(created_at__year=current_year).first()

        if existing_record:
            # Clean up the tasks linked to existing_record
            tasks_to_remove = []
            for task in existing_record.task.all():
                # Check if the task exists and has a 'Completed' status
                if not Task.objects.filter(pk=task.pk).exists() or task.task_status != 'Completed':
                    tasks_to_remove.append(task)
            if tasks_to_remove:
                existing_record.task.remove(*tasks_to_remove)
            serializer = self.get_serializer(existing_record)
            return Response([serializer.data], status=status.HTTP_200_OK)  # Return as a list
        else:
            # Create a new record for the current year and user's organization
            organization = None if user.is_superuser else user.organization
            new_record = ProcedureReview.objects.create(
                organization=organization,
                created_by=user,
            )
            serializer = self.get_serializer(new_record)
            return Response([serializer.data], status=status.HTTP_201_CREATED)  # Return as a list

    def create(self, request, *args, **kwargs):
        """
        Only allow 'CCO' users to create ProcedureReview records.
        Ensure that only one record exists for a given organization and year.
        """
        user = request.user

        # Allow only 'CCO' users to create records
        if not user.is_superuser and user.role != 'CCO':
            raise PermissionDenied("Only CCO users can create ProcedureReview records.")

        # Check for an existing record for the current year
        current_year = datetime.now().year

        # Check if a ProcedureReview record for the current year already exists for the user's organization
        existing_record = ProcedureReview.objects.filter(
            created_at__year=current_year, organization=user.organization
        ).first()

        if existing_record:
            raise serializers.ValidationError(
                {"detail": "A ProcedureReview record for the current year already exists for your organization."}
            )

        # Copy the request data
        data = request.data.copy()

        # Handle task_ids
        task_ids = data.get('task_ids', [])
        if isinstance(task_ids, str):
            task_ids = [int(id) for id in task_ids.split(',') if id.strip().isdigit()]
        data.setlist('task_ids', task_ids)

        # Pass the modified data to the serializer
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=user, organization=user.organization)

        return Response({"status": "success", 'message': 'ProcedureReview created successfully.'},
                        status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """
        Allow 'CCO' users to update ProcedureReview records.
        """
        user = request.user

        # Allow only 'CCO' users to update records
        if not user.is_superuser and user.role != 'CCO':
            raise PermissionDenied("Only CCO users can update ProcedureReview records.")

        # Copy the request data
        data = request.data.copy()

        # Handle task_ids
        task_ids = data.get('task_ids', [])
        if isinstance(task_ids, str):
            task_ids = [int(id) for id in task_ids.split(',') if id.strip().isdigit()]
        data.setlist('task_ids', task_ids)

        # Pass the modified data to the serializer
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"status": "success", 'message': 'ProcedureReview updated successfully.'},
                        status=status.HTTP_200_OK)
