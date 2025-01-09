from rest_framework import serializers
from fiduciary.models import SignUpInvitation
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

CustomUser = get_user_model() 

class SignUpInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignUpInvitation
        fields = ['email']  # You can add other fields if necessary

    def validate_email(self, value):
        # You can add custom validation logic here
        if SignUpInvitation.objects.filter(email=value).exists():
            raise serializers.ValidationError("An invitation has already been sent to this email.")
        return value



class SignupSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    phone_number = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate_email(self, value):
        """
        Validate that the email is unique and not already in use.
        """
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError({
                "status": "error",
                "message": _("A user with this email already exists. Please use a different email or login to your existing account.")
            })
        return value

    def validate(self, attrs):
        # You can add additional validations here if needed
        return attrs

    def create(self, validated_data):
        # Create and return a new user instance
        user = CustomUser.objects.create_user(
            username=validated_data['email'],  # Using email as the username
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user
