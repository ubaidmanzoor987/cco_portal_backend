import json
from .serializers import *
from navbar.models import *
from botocore.exceptions import ClientError
from utils.s3_utils import upload_file_to_s3, initialize_s3_client

from django.db import DataError
from django.forms import ValidationError
from django.shortcuts import get_object_or_404

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from acr_tool.permissions import IsSuperUser
from drf_yasg.inspectors import SwaggerAutoSchema


class OrganizationSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['Organization']


class BasicFileUploadTemplateSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['Basic File Upload Template']


class OrganizationCreateView(generics.CreateAPIView):
    serializer_class = OrganizationCreateSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsSuperUser]
    parser_classes = (MultiPartParser, FormParser)
    swagger_schema = OrganizationSwaggerAutoSchema

    def create(self, request, *args, **kwargs):
        image_data = request.FILES.get('image')

        try:
            if image_data:
                upload_file_to_s3(image_data)

            validated_data = self.get_validated_data(request, image_data)
            organization = self.save_serializer(validated_data)  # Save Organization instance
            organization_id = str(organization.id)

            folder_name = f'organization_data/{organization.company_name}_{organization_id}'

            self.create_folder_on_s3(folder_name)

            # Update OrganizationParentNavBar and OrganizationSubNavBar
            self.create_navbars(organization)

            return Response({
                'status': 'success',
                'message': 'Organization and CustomUser successfully created.',
                'organization_id': organization.id,
                'company_name': organization.company_name,
                'company_number': str(organization.company_number),
                'contract_duration': organization.contract_duration,
                'email_address': organization.email_address,
                'onboarding_date': organization.onboarding_date,
                'contract_periods': organization.contract_periods,
            }, status=status.HTTP_201_CREATED)

        except NoCredentialsError:
            return Response({'status': 'error', 'detail': 'AWS credentials not available.'},
                            status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response({'status': 'error', 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'detail': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)

    def get_validated_data(self, request, image_data):
        contract_duration = request.data.get('contract_duration', None)

        # Ensure 'contract_duration' is a positive integer
        if contract_duration is not None:
            try:
                contract_duration = int(contract_duration)
                if contract_duration <= 0:
                    raise ValueError('contract_duration must be a positive integer.')
            except ValueError:
                raise Response({'status': 'error', 'detail': 'contract_duration must be a positive integer.'},
                               status=status.HTTP_400_BAD_REQUEST)

        validated_data = {
            'company_name': request.data.get('company_name'),
            'company_number': request.data.get('company_number'),
            'contract_duration': contract_duration,
            'contract_periods': request.data.get('contract_periods'),
            'email_address': request.data.get('email_address'),
            'onboarding_date': request.data.get('onboarding_date'),
            'company_address': request.data.get('company_address'),
            'username': request.data.get('username'),
            'email': request.data.get('email'),
            'password': request.data.get('password'),
            'active_duration': request.data.get('active_duration'),
            'active_periods': request.data.get('active_periods'),
        }

        # Include 'image' in validated_data if it is present in the request data
        if image_data:
            validated_data['image'] = image_data

        return validated_data

    def save_serializer(self, validated_data):
        serializer = self.get_serializer(data=validated_data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return instance

    def create_navbars(self, organization):
        # Get all NavBars and SubNavBars
        navbars = NavBar.objects.all()
        sub_navbars = SubNavBar.objects.all()

        # Create OrganizationParentNavBar for each NavBar
        for navbar in navbars:
            OrganizationParentNavBar.objects.create(
                organization=organization,
                navbar=navbar,
                enable=False,
                display_name=navbar.name
            )

        # Create OrganizationSubNavBar for each SubNavBar
        for subnavbar in sub_navbars:
            OrganizationSubNavBar.objects.create(
                organization=organization,
                subnavbar=subnavbar,
                enable=False,
                navbar=subnavbar.navbar
            )

    def create_folder_on_s3(self, folder_name):
        s3 = initialize_s3_client()
        s3.put_object(Bucket=config('S3_BUCKET_NAME'), Key=f'{folder_name}/')


class OrganizationDeleteView(generics.DestroyAPIView):
    queryset = Organization.objects.all()
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsSuperUser]
    swagger_schema = OrganizationSwaggerAutoSchema

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object_or_none()

        if not instance:
            return Response({'status': 'error', 'detail': 'Organization not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Delete the database record
            instance.delete()
            return Response({'status': 'success', 'message': 'Organization successfully deleted.'},
                            status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'status': 'error', 'detail': f'Error deleting organization: {str(e)}'},
                            status=status.HTTP_400_BAD_REQUEST)

    def get_object_or_none(self):
        return get_object_or_404(self.queryset, pk=self.kwargs.get('pk', None))


class OrganizationListView(generics.ListAPIView):
    queryset = Organization.objects.all()
    serializer_class = OrganizationUpdateSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    swagger_schema = OrganizationSwaggerAutoSchema


class OrganizationRetrieveView(generics.RetrieveAPIView):
    queryset = Organization.objects.all()
    serializer_class = OrganizationViewSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    swagger_schema = OrganizationSwaggerAutoSchema


class OrganizationUpdateView(generics.UpdateAPIView):
    queryset = Organization.objects.all()
    serializer_class = OrganizationUpdateSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsSuperUser]
    parser_classes = (MultiPartParser, FormParser)
    swagger_schema = OrganizationSwaggerAutoSchema

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        image_data = request.FILES.get('image')

        try:
            if image_data:
                upload_file_to_s3(image_data)
                instance.s3_file_link = f'https://{config("S3_BUCKET_NAME")}.s3.amazonaws.com/{image_data.name}'

            validated_data = self.get_validated_data(request, image_data)
            serializer = self.get_serializer(instance, data=validated_data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            return Response({
                'status': 'success',
                'message': 'Organization successfully updated.',
                'organization_id': instance.id
            }, status=status.HTTP_200_OK)

        except NoCredentialsError:
            return Response({'status': 'error', 'detail': 'AWS credentials not available.'},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get_validated_data(self, request, image_data):
        contract_duration = request.data.get('contract_duration', None)

        # Ensure 'contract_duration' is a positive integer
        if contract_duration is not None:
            try:
                contract_duration = int(contract_duration)
                if contract_duration <= 0:
                    raise ValueError('contract_duration must be a positive integer.')
            except ValueError:
                raise Response({'status': 'error', 'detail': 'contract_duration must be a positive integer.'},
                               status=status.HTTP_400_BAD_REQUEST)

        validated_data = {
            'company_name': request.data.get('company_name'),
            'company_number': request.data.get('company_number'),
            'company_contact': request.data.get('company_contact'),
            'contract_duration': contract_duration,
            'contract_periods': request.data.get('contract_periods'),
            'email_address': request.data.get('email_address'),
            'onboarding_date': request.data.get('onboarding_date'),
            'company_address': request.data.get('company_address'),
            'description': request.data.get('description'),
        }

        # Include 'image' in validated_data if it is present in the request data
        if image_data:
            validated_data['image'] = image_data

        # Include org_tasks_uuids if present
        org_tasks_uuids = request.data["org_tasks_uuids"].split(",")
        if org_tasks_uuids:
            validated_data['org_tasks_uuids'] = org_tasks_uuids

        return validated_data


class CustomOrganizationViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserOrganizationSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    swagger_schema = OrganizationSwaggerAutoSchema

    @action(detail=False, methods=['GET'])
    def users_by_organization(self, request, organization_id=None):
        if organization_id:
            users = self.queryset.filter(organization_id=organization_id)
            serializer = self.get_serializer(users, many=True)
            return Response(serializer.data)
        else:
            return Response({'status': 'error', 'detail': 'Organization ID is required'},
                            status=status.HTTP_400_BAD_REQUEST)


class BasicTemplateViewSet(viewsets.ModelViewSet):
    queryset = BasicTemplate.objects.all()
    serializer_class = BasicTemplateSerializer
    parser_classes = (MultiPartParser, FormParser)
    swagger_schema = BasicFileUploadTemplateSwaggerAutoSchema

    @action(detail=False, methods=['post'])
    def upload_files(self, request):
        try:
            bucket_name = config('S3_BUCKET_NAME')
            s3 = initialize_s3_client()

            # Extract data from the request
            name = request.data.get('name')
            basic_html = request.data.get('basic_html')
            data_json = {'name': name, 'files': []}

            # Check if the name already exists
            if BasicTemplate.objects.filter(name=name).exists():
                return Response(
                    {'status': 'error', "detail": "A template with this name already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create folder on S3 for the basic templates
            folder_name = f'basic_templates/{name}/'
            s3.put_object(Bucket=bucket_name, Key=(folder_name + '/'))

            # Upload the basic HTML file to S3
            basic_html_s3_link = None
            if basic_html:
                basic_html_name = basic_html.name
                s3_key_basic_html = folder_name + basic_html_name
                s3.upload_fileobj(basic_html, bucket_name, s3_key_basic_html)
                basic_html_s3_link = f"https://{bucket_name}.s3.amazonaws.com/{s3_key_basic_html}"

            # Upload other files to S3 and update data_json
            for i in range(1, 6):
                file_key = f'file{i}'
                if file_key in request.FILES:
                    file_obj = request.FILES[file_key]
                    file_name = file_obj.name
                    s3_key = folder_name + file_name
                    s3.upload_fileobj(file_obj, bucket_name, s3_key)
                    data_json['files'].append({
                        'file_name': file_name,
                        'file_link': f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"
                    })

            # Create or update BasicTemplate object
            basic_template, _ = BasicTemplate.objects.update_or_create(
                name=name,
                defaults={'basic_html': basic_html_s3_link, 'data_json': data_json}
            )

            response_data = {
                'status': 'success',
                "message": "Template uploaded successfully.",
                "template": {
                    "name": basic_template.name,
                    "id": basic_template.id,
                    "basic_html": basic_template.basic_html.url,
                }
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        except ClientError as e:
            error_message = "An error occurred while uploading the template files."
            return Response({'status': 'error', "detail": error_message}, status=status.HTTP_400_BAD_REQUEST)
        except DataError as e:
            error_message = "A database error occurred."
            return Response({'status': 'error', "detail": error_message}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', "detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
