from utils.s3_utils import upload_file_to_s3
from .models import *
from rest_framework.authtoken.models import Token
from task.models import *
from rest_framework import serializers
from django.contrib.auth import get_user_model
from botocore.exceptions import NoCredentialsError
from decouple import config


class CustomUserCreateSerializer(serializers.ModelSerializer):
    image = serializers.FileField(write_only=True, required=False)
    active_duration = serializers.IntegerField(write_only=True, required=True)
    organization = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = get_user_model()
        fields = ['id', 'email', 'username', 'active_duration', 'active_periods', 'password', 'number', 'organization',
                  'role', 'description', 'image']
        read_only_fields = ['s3_image_link']

    def validate_active_duration(self, value):
        if value <= 0:
            raise serializers.ValidationError("active_duration must be a positive integer.")
        return value

    def create(self, validated_data):
        global user_instance
        image_data = validated_data.pop('image', None)
        organization_name = validated_data.pop('organization', None)

        # Get the organization instance
        organization_instance = self.get_organization_instance(organization_name)
        validated_data['organization'] = organization_instance
        user_instance = get_user_model().objects.create_user(**validated_data)
        if image_data:
            try:
                upload_file_to_s3(image_data)
                bucket_name = config('S3_BUCKET_NAME')
                user_instance.s3_image_link = f'https://{bucket_name}.s3.amazonaws.com/{image_data.name}'
                user_instance.save()
            except NoCredentialsError:
                raise serializers.ValidationError({'error': 'AWS credentials not available.'})
            except Exception as e:
                raise serializers.ValidationError({'error': f'Error uploading image to S3: {str(e)}'})

        # Assign organization tasks to the new user
        self.assign_organization_tasks_to_user(user_instance, organization_instance)

        return user_instance

    def get_organization_instance(self, organization_name):
        try:
            return Organization.objects.get(company_name=organization_name)
        except Organization.DoesNotExist:
            raise serializers.ValidationError({'error': f'Organization with name {organization_name} does not exist.'})

    def assign_organization_tasks_to_user(self, user_instance, organization_instance):
        """
        Fetch tasks associated with the organization and assign them to the user.
        """
        organization_tasks = OrganizationTask.objects.filter(organization=organization_instance)
        for org_task in organization_tasks:
            OrganizationUserTask.objects.get_or_create(
                organization=organization_instance,
                organization_user=user_instance,
                task=org_task.task
            )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.pop('password', None)  # Exclude the password field from the response
        return data


class CustomUserUpdateSerializer(serializers.ModelSerializer):
    image = serializers.FileField(write_only=True, required=False)
    active_duration = serializers.IntegerField(write_only=True, required=True)
    organization = serializers.CharField(write_only=True, required=True)
    is_active = serializers.BooleanField(write_only=True, required=True)

    class Meta:
        model = get_user_model()
        fields = ['id', 'email', 'username', 'active_duration', 'active_periods', 'number', 'organization',
                  'role', 'description', 'image', 'is_active']
        read_only_fields = ['s3_image_link']

    def validate_active_duration(self, value):
        if value <= 0:
            raise serializers.ValidationError("active_duration must be a positive integer.")
        return value

    def update(self, instance, validated_data):
        organization_name = validated_data.pop('organization', None)

        # Update the organization instance if 'organization' is present in the update data
        if organization_name:
            organization_instance = self.get_organization_instance(organization_name)
            instance.organization = organization_instance

        for key, value in validated_data.items():
            setattr(instance, key, value)

        instance.save()
        return instance

    def get_organization_instance(self, organization_name):
        try:
            return Organization.objects.get(company_name=organization_name)
        except Organization.DoesNotExist:
            raise serializers.ValidationError({'error': f'Organization with name {organization_name} does not exist.'})

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.pop('password', None)  # Exclude the password field from the response
        return data


class UserSerializer(serializers.ModelSerializer):
    # Add a new field for organization_name
    organization_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'organization', 'organization_name', 'role', 'number', 'active_duration',
                  'active_periods', 'is_active', 'description', 's3_image_link', 'created_with_org']

    def get_organization_name(self, obj):
        # Get the organization name if available
        if obj.organization:
            return obj.organization.company_name
        return None


class UserDeleteSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class CCOLoginResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = (
            'email', 'username', 'active_duration', 'active_periods', 'number', 'organization', 'role', 'description',
            's3_image_link'
        )


class UserTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Token
        fields = ['key']


class FBGetCurrentUserSerializer(serializers.Serializer):
    pass


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    new_password = serializers.CharField(write_only=True)
