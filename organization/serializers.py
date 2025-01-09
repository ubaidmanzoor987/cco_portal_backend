# serializers.py
from accounts.serializers import CustomUserCreateSerializer
from .models import *
from accounts.models import CustomUser
from rest_framework import serializers
from decouple import config
from accounts.views import schedule_set_user_inactive
from accounts.serializers import *
from task.models import *
from rest_framework.parsers import MultiPartParser, FormParser


class OrganizationCreateSerializer(serializers.ModelSerializer):
    image = serializers.FileField(write_only=True, required=False)
    username = serializers.CharField(max_length=30, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        style={'input_type': 'password'}
    )
    active_duration = serializers.IntegerField(required=True)
    ACTIVE_PERIODS = [
        ('Hours', 'Hours'),
        ('Months', 'Months'),
        ('Years', 'Years'),
    ]

    active_periods = serializers.ChoiceField(
        choices=ACTIVE_PERIODS,
        required=True
    )

    class Meta:
        model = Organization
        fields = ['id', 'company_name', 'company_number', 'contract_duration', 'contract_periods',
                  'email_address', 'onboarding_date', 'company_address', 'image', 's3_file_link',
                  'username', 'email', 'password', 'active_duration', 'active_periods']
        read_only_fields = ['s3_file_link']

    def create(self, validated_data):
        bucket_name = config('S3_BUCKET_NAME')
        file_data = validated_data.pop('image', None)

        keys_to_pop = ['username', 'email', 'password', 'active_duration', 'active_periods']
        user_data = {key: validated_data.pop(key) for key in keys_to_pop}

        email = user_data.get('email')
        custom_user_instance = CustomUser.objects.filter(email=email)
        if custom_user_instance.exists():
            raise serializers.ValidationError({'error': 'User with this email id already exists.'})

        instance = super().create(validated_data)

        user_data['organization'] = instance.company_name
        user_instance = self.create_custom_user(user_data)

        # If 'file' is present, set 's3_file_link' based on the S3 file path
        if file_data:
            s3_file_path = f'https://{bucket_name}.s3.amazonaws.com/{file_data.name}'
            instance.s3_file_link = s3_file_path
            instance.save()

        schedule_set_user_inactive(user_instance.id, user_instance.active_duration, user_instance.active_periods)
        return instance

    def create_custom_user(self, user_data):
        # Customize this based on your actual fields in CustomUser model
        custom_user_serializer = CustomUserCreateSerializer(data=user_data)
        custom_user_serializer.is_valid(raise_exception=True)
        instance = custom_user_serializer.save()
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['organization_id'] = instance.id
        return representation


class OrganizationUpdateSerializer(serializers.ModelSerializer):
    image = serializers.FileField(write_only=True, required=False)
    org_tasks_uuids = serializers.ListField(
        child=serializers.CharField(
            allow_blank=False
        ),
        write_only=True,
        required=False
    )

    class Meta:
        model = Organization
        fields = [
            'id', 'company_name', 'company_number', 'company_contact', 'contract_duration', 'contract_periods',
            'email_address', 'onboarding_date', 'company_address', 'description', 'image', 's3_file_link', 'org_tasks_uuids'
        ]
        read_only_fields = ['s3_file_link']

    def validate_contract_duration(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError('contract_duration must be a positive integer.')
        return value

    def update(self, instance, validated_data):
        org_tasks_uuids = validated_data.pop('org_tasks_uuids', None)

        if org_tasks_uuids:
            self.assign_tasks_to_organization(instance, org_tasks_uuids)

        return super().update(instance, validated_data)

    def assign_tasks_to_organization(self, organization, org_tasks_uuids):
        tasks = Task.objects.filter(task_uuid__in=org_tasks_uuids)

        # Clear existing tasks to avoid duplicates or inconsistencies
        # OrganizationTask.objects.filter(organization=organization).delete()
        # OrganizationUserTask.objects.filter(organization=organization).delete()

        # Assign tasks to organization and its users
        for task in tasks:
            OrganizationTask.objects.update_or_create(organization=organization, task=task)

            organization_users = CustomUser.objects.filter(organization=organization)
            for user in organization_users:
                OrganizationUserTask.objects.update_or_create(
                    organization=organization,
                    organization_user=user,
                    task=task
                )


class OrganizationViewSerializer(serializers.ModelSerializer):
    image = serializers.FileField(write_only=True, required=False)
    comapny_contact = serializers.SerializerMethodField()  # Field to represent usernames

    class Meta:
        model = Organization
        fields = ['id', 'company_name', 'company_number', 'comapny_contact', 'contract_duration', 'contract_periods',
                  'email_address', 'onboarding_date', 'company_address', 'description', 'image', 's3_file_link']
        read_only_fields = ['s3_file_link']

    def get_comapny_contact(self, obj):
        # Retrieve usernames of associated users with created_with_org=True
        users = CustomUser.objects.filter(organization=obj, created_with_org=True)
        return [user.username for user in users]


class CustomUserOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = '__all__'


class BasicTemplateSerializer(serializers.ModelSerializer):
    file1 = serializers.FileField(required=False)
    file2 = serializers.FileField(required=False)
    file3 = serializers.FileField(required=False)
    file4 = serializers.FileField(required=False)
    file5 = serializers.FileField(required=False)

    class Meta:
        model = BasicTemplate
        fields = ['name', 'basic_html', 'file1', 'file2', 'file3', 'file4', 'file5']
