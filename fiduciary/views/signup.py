from rest_framework import viewsets, status
from rest_framework.response import Response
from fiduciary.models import *
from fiduciary.serializers import *
from rest_framework.permissions import AllowAny, IsAuthenticated

from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives 
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_bytes
from fiduciary.swagger_schema import *
from rest_framework.authtoken.models import Token 


class SignUpInvitationViewSet(viewsets.ModelViewSet):
    serializer_class = SignUpInvitationSerializer
    permission_classes = [IsAuthenticated]
    swagger_schema = FiduciaryAccountsSwaggerAutoSchema

    def create(self, request, *args, **kwargs):
        if request.user.role != 'CCO':  # Check if the user is a CCO
            return Response({
                "status": "error",
                "message": "You do not have permission to send invitations."
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "status": "error",
                "message": "There was an error validating the invitation data.",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']

        # Check if there is already an active invitation for this email
        existing_invitation = SignUpInvitation.objects.filter(email=email, is_used=False).first()
        if existing_invitation:
            return Response({
                "status": "error",
                "message": "This email already has an active invitation link."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create the invitation if no existing invitation is found
        invitation = SignUpInvitation(email=email)

        combined = f"{invitation.secret_key}:{email}"
        token = urlsafe_base64_encode(force_bytes(combined))

        # invitation_link = f"http://localhost:3000/signup?token={token}"
        
        invitation_link = f"https://fudiciary-tool.vercel.app/signup?token={token}"

        context = {
            'advisor_name': email.split('@')[0],
            'invitation_link': invitation_link,
        }
        html_content = render_to_string('invitation_email.html', context)

        email_subject = 'Your Invitation Link'
        email_from = settings.DEFAULT_FROM_EMAIL
        email_to = [email]

        email_message = EmailMultiAlternatives(
            subject=email_subject,
            body='This is the fallback text if the HTML is not displayed.',
            from_email=email_from,
            to=email_to,
        )
        email_message.attach_alternative(html_content, "text/html")

        try:
            email_message.send(fail_silently=False)
            invitation.save()  # Only save if email is sent successfully
        except Exception as e:
            return Response({
                "status": "error",
                "message": "There was an error sending the invitation email.",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "status": "success",
            "message": "Invitation sent successfully."
        }, status=status.HTTP_201_CREATED)



class SignUpViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = SignupSerializer
    swagger_schema = FiduciaryAccountsSwaggerAutoSchema
    
    def post(self, request):
        token = request.query_params.get("token")

        if not token:
            return Response({
                "status": "error",
                "message": "A valid token is required to proceed with the signup process."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded_data = urlsafe_base64_decode(token).decode()
            secret_key, email = decoded_data.split(":")
        except Exception:
            return Response({
                "status": "error",
                "message": "The provided invitation token is invalid."
            }, status=status.HTTP_400_BAD_REQUEST)

        invitation = SignUpInvitation.objects.filter(secret_key=secret_key, email=email, is_used=False).first()

        if not invitation or invitation.expiration_date < timezone.now():
            return Response({
                "status": "error",
                "message": "The invitation is either invalid or has expired. Please request a new invitation."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Use the serializer to validate and create the user
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Assign the role of 'Advisor'
            user.role = 'Advisor'
            user.save()

            # Mark the invitation as used
            invitation.is_used = True
            invitation.save()

            # Generate authentication token for the user
            token, created = Token.objects.get_or_create(user=user)

            return Response({
                "status": "success",
                "message": "Your account has been created successfully. Welcome aboard!",
                "user_id": user.id,
                "token": token.key  # Return the token in the response
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "status": "error",
                "message": "There was an issue with your registration details. Please check the information provided.",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
