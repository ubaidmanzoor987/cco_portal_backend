import re
import logging

from django.core.exceptions import ObjectDoesNotExist
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model, logout
from rest_framework.authtoken.models import Token
from rest_framework.generics import GenericAPIView
from rest_framework import status, generics
from rest_framework.parsers import MultiPartParser, FormParser
from celery.result import AsyncResult

from botocore.exceptions import NoCredentialsError
from decouple import config

from utils.s3_utils import upload_file_to_s3
from .models import CustomUser
from .serializers import (
    CustomUserCreateSerializer, CustomUserUpdateSerializer,
    UserLoginSerializer, UserSerializer, UserDeleteSerializer, FBGetCurrentUserSerializer, PasswordResetSerializer,
    CCOLoginResponseSerializer,
)

from accounts import task
from django.utils import timezone
from navbar.serializers import *
from accounts.swagger_schema import *

logger = logging.getLogger(__name__)


def schedule_set_user_inactive(user_id, active_duration, active_periods):
    user = CustomUser.objects.get(pk=user_id)
    current_time = timezone.now()

    # Calculate the timedelta based on active_periods
    if active_periods == 'Hours':
        timedelta = timezone.timedelta(hours=active_duration)
    elif active_periods == 'Months':
        timedelta = timezone.timedelta(days=active_duration * 30)  # Assuming 30 days per month
    elif active_periods == 'Years':
        timedelta = timezone.timedelta(days=active_duration * 365)  # Assuming 365 days per year
    else:
        raise ValueError("Invalid active period")

    scheduled_time = current_time + timedelta

    delay = (scheduled_time - current_time).total_seconds()

    task_result = task.set_user_inactive.apply_async(args=[user_id], countdown=delay)

    # Save the task ID to the celery_task_id field
    user.celery_task_id = task_result.id
    user.save()


class UserSignupView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserCreateSerializer
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)
    swagger_schema = UsersSwaggerAutoSchema

    def post(self, request, *args, **kwargs):
        provided_email = request.data.get("email", None)

        try:
            if CustomUser.objects.filter(email=provided_email).exists():
                return self._response_error("Email already exists. Please use a different email.")

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)

            response_data = {
                "status": "success",
                "message": "Account created successfully.",
                "data": {
                    'username': serializer.data['username'],
                    'email': serializer.data['email']
                }
            }

            # Get the user instance and schedule the task
            user_instance = serializer.instance
            user_instance.created_with_org = False
            user_instance.save()

            schedule_set_user_inactive(user_instance.id, user_instance.active_duration, user_instance.active_periods)

            return Response(
                response_data, status=status.HTTP_201_CREATED, headers=headers
            )

        except Exception as e:
            return self._response_error("Invalid input or user already exists.", errors=str(e))

    def perform_create(self, serializer):
        serializer.save()

    def _response_error(self, message, errors=None):
        response_data = {
            "status": "error",
            "detail": message,
        }
        if errors:
            pattern = r"ErrorDetail\(string='([^']+)',"
            match = re.search(pattern, errors)
            response_data['detail'] = match.group(1)

        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)


class UserListView(generics.ListAPIView):
    queryset = CustomUser.objects.filter(is_superuser=False)
    serializer_class = UserSerializer
    swagger_schema = UsersSwaggerAutoSchema


class UserDetailView(generics.RetrieveAPIView):
    queryset = CustomUser.objects.filter(is_superuser=False)
    serializer_class = UserSerializer
    swagger_schema = UsersSwaggerAutoSchema


class UserUpdateView(generics.UpdateAPIView):
    queryset = get_user_model().objects.all()
    serializer_class = CustomUserUpdateSerializer
    parser_classes = (MultiPartParser, FormParser)
    swagger_schema = UsersSwaggerAutoSchema

    def update(self, request, *args, **kwargs):
        user_id = kwargs.get('pk')

        try:
            instance = get_user_model().objects.get(pk=user_id)
        except get_user_model().DoesNotExist:
            return self.error_response(message=f'User with ID {user_id} does not exist.',
                                       status_code=status.HTTP_404_NOT_FOUND)

        is_active_changed = 'is_active' in request.data and instance.is_active != (
                request.data['is_active'].lower() == 'true')
        celery_task_id = instance.celery_task_id
        image_data = request.data.get('image', None)

        try:
            if image_data:
                upload_file_to_s3(image_data)
                bucket_name = config('S3_BUCKET_NAME')
                instance.s3_image_link = f'https://{bucket_name}.s3.amazonaws.com/{image_data.name}'

            if is_active_changed:
                self.terminate_celery_task(celery_task_id)

            if request.data['is_active'].lower() == 'false':
                self.update_inactive_user(instance, request)

            elif request.data['active_duration'] and request.data['is_active'].lower() == 'true':
                self.update_active_user(instance, request, celery_task_id)

            self.perform_serializer_update(instance, request)

            response_data = self.serializer_class(instance).to_representation(instance)
            return self.success_response(response_data)
        except NoCredentialsError:
            return self.error_response(message='AWS credentials not available.',
                                       status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return self.error_response(status_code=status.HTTP_400_BAD_REQUEST, errors=str(e))

    def terminate_celery_task(self, celery_task_id):
        if celery_task_id:
            task_result = AsyncResult(celery_task_id)
            task_result.revoke(terminate=True)
            print("Previous task terminated!")

    def update_inactive_user(self, instance, request):
        instance.active_duration = request.data['active_duration']
        instance.is_active = request.data.get('is_active', '').lower() == 'true'
        instance.save()
        self.perform_serializer_update(instance, request)

    def update_active_user(self, instance, request, celery_task_id):
        if int(request.data['active_duration']) <= 0:
            raise self.error_response(message='Please provide a correct active duration',
                                      status_code=status.HTTP_400_BAD_REQUEST)
        self.terminate_celery_task(celery_task_id)
        schedule_set_user_inactive(instance.id, int(request.data['active_duration']), request.data['active_periods'])

    def perform_serializer_update(self, instance, request):
        instance.active_duration = request.data['active_duration']
        instance.is_active = request.data.get('is_active', '').lower() == 'true'
        instance.save()

        serializer = self.get_serializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

    def success_response(self, data):
        return Response({'status': 'success', 'data': data}, status=status.HTTP_200_OK)

    def error_response(self, message=None, status_code=None, errors=None):
        if errors:
            if 'ErrorDetail' in errors:
                pattern = r"ErrorDetail\(string='([^']+)',"
                match = re.search(pattern, errors)
                message = match.group(1)
            else:
                message = errors

        return Response({'status': 'error', 'detail': message}, status=status_code)


class UserDeleteView(generics.DestroyAPIView):
    serializer_class = UserDeleteSerializer
    swagger_schema = UsersSwaggerAutoSchema

    def destroy(self, request, *args, **kwargs):
        user_id = self.kwargs.get('user_id')
        serializer = self.get_serializer(data={'user_id': user_id})
        serializer.is_valid(raise_exception=True)

        try:
            user_to_delete = CustomUser.objects.get(id=user_id, is_superuser=False)
            user_to_delete.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except CustomUser.DoesNotExist:
            return Response({'status': 'error', 'detail': 'User not found or is a superuser.'},
                            status=status.HTTP_404_NOT_FOUND)


class UserLoginView(GenericAPIView):
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]
    swagger_schema = AccountSwaggerAutoSchema

    def post(self, request):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            email = serializer.validated_data["email"]
            password = serializer.validated_data["password"]

            try:
                user = get_user_model().objects.get(email=email)
            except ObjectDoesNotExist:
                return self.error_response("Invalid username or password. Please try again.",
                                           status.HTTP_401_UNAUTHORIZED)

            if user.check_password(password):
                if user.is_superuser:
                    token, created = Token.objects.get_or_create(user=user)
                    return self.success_response({"token": token.key})
                else:
                    return self.error_response("Only admin users are allowed to login.", status.HTTP_401_UNAUTHORIZED)

            return self.error_response("Invalid username or password. Please try again.", status.HTTP_401_UNAUTHORIZED)

        except Exception as e:
            return self.error_response(serializer.errors, status.HTTP_400_BAD_REQUEST)

    def success_response(self, data=None):
        return Response({
            "status": "success",
            "message": "Logged in successfully.",
            "data": data or {}
        })

    def error_response(self, detail, status_code):
        return Response({
            "status": "error",
            "detail": detail,
        }, status=status_code)


from rest_framework import viewsets


class LoginView(viewsets.ModelViewSet):
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]
    swagger_schema = AccountSwaggerAutoSchema

    def login_CCO(self, request, *args, **kwargs):
        return self.login_user(request, role_required="CCO", include_navbar=True)

    def login_fiduciary(self, request, *args, **kwargs):
        return self.login_user(request, role_required=["CCO", "Advisor"], include_navbar=False)

    def login_user(self, request, role_required, include_navbar=False):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            email = serializer.validated_data["email"]
            password = serializer.validated_data["password"]
            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                return self.error_response("Invalid username or password. Please try again.",
                                           status.HTTP_401_UNAUTHORIZED)

            if not user.is_active:
                return self.error_response("Your account has been disabled. Please contact support for assistance.",
                                           status.HTTP_401_UNAUTHORIZED)

            if user.check_password(password):

                if user.is_superuser:
                    return self.error_response("Superusers are not allowed to login on this Portal!",
                                               status.HTTP_401_UNAUTHORIZED)

                if isinstance(role_required, list):
                    allowed_roles = role_required
                else:
                    allowed_roles = [role_required]

                if user.role in allowed_roles:
                    token, created = Token.objects.get_or_create(user=user)

                    response_data = {
                        "token": token.key,
                    }

                    if user.role == "CCO" and include_navbar:
                        organization_id = user.organization_id
                        navbar_data = self.get_navbar_data(organization_id)
                        response_data["navbar_data"] = navbar_data
                        user_data = CCOLoginResponseSerializer(user).data
                        response_data = {
                            "token": token.key,
                            "navbar_data": navbar_data,
                            "user_data": user_data
                        }

                    return self.success_response("Logged in successfully.", response_data)

                else:
                    return self.error_response("Only CCO users are allowed to log in.", status.HTTP_401_UNAUTHORIZED)

            return self.error_response("Invalid username or password. Please try again.", status.HTTP_401_UNAUTHORIZED)

        except Exception as e:
            return self.error_response(serializer.errors, status.HTTP_400_BAD_REQUEST)

    def get_navbar_data(self, org_id):
        if org_id:
            parent_navbars = OrganizationParentNavBar.objects.filter(organization_id=org_id)
            parent_serializer = OrganizationParentNavBarSerializer(parent_navbars, many=True).data
            sub_navbars = OrganizationSubNavBar.objects.filter(organization_id=org_id)
            sub_serializer = OrganizationSubNavBarSerializer(sub_navbars, many=True).data

            for parent_navbar in parent_serializer:
                parent_id = parent_navbar['navbar']
                navbar_instance = NavBar.objects.get(id=parent_id)
                parent_navbar['narbar_link'] = navbar_instance.link
                parent_navbar['sub_navbars'] = []

                for sub_navbar in sub_serializer:
                    if sub_navbar['navbar'] == parent_id:
                        sub_navbar_instance = SubNavBar.objects.get(id=sub_navbar['subnavbar'])
                        sub_navbar_link = sub_navbar_instance.link

                        sub_navbar_data = {
                            'id': sub_navbar['id'],
                            'enable': sub_navbar['enable'],
                            'subnavbar': sub_navbar['subnavbar'],
                            'organization': sub_navbar['organization'],
                            'navbar': sub_navbar['navbar'],
                            'subnavbar_name': sub_navbar_instance.name,
                            'subnavbar_display_name': sub_navbar_instance.display_name,
                            'sub_navbar_link': sub_navbar_link
                        }
                        parent_navbar['sub_navbars'].append(sub_navbar_data)
            return parent_serializer
        else:
            return {'error': 'Please provide an org_id parameter.'}

    def success_response(self, message, data=None):
        return Response({
            "status": "success",
            "message": message,
            "data": data or {}
        })

    def error_response(self, message, status_code):
        return Response({
            "status": "error",
            "detail": message,
        }, status=status_code)


class UserLogoutView(APIView):
    swagger_schema = AccountSwaggerAutoSchema

    def post(self, request):
        logout(request)
        return Response({"status": "success", "message": "Logged out successfully."}, status=status.HTTP_200_OK)


class FBGetCurrentUserView(GenericAPIView):
    serializer_class = FBGetCurrentUserSerializer
    swagger_schema = CurrentUserSwaggerAutoSchema

    def get(self, request):
        try:
            user = request.user
            user_data = {

                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
            }
            return Response(user_data, status=status.HTTP_200_OK)
        except:
            return Response({
                'status': 'error',
                'detail': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]
    swagger_schema = AccountSwaggerAutoSchema

    @swagger_auto_schema(
        request_body=PasswordResetSerializer,
        responses={200: 'Password reset successful', 400: 'Bad Request'},
    )
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data.get('email')
        new_password = serializer.validated_data.get('new_password')

        # Check if the authenticated user is a superuser
        if not request.user.is_superuser:
            return Response({'status': 'error', 'detail': 'You do not have permission to reset the password.'},
                            status=status.HTTP_403_FORBIDDEN)

        # Retrieve the user based on the provided email
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({'status': 'error', 'detail': 'User with the provided email does not exist.'},
                            status=status.HTTP_404_NOT_FOUND)

        # Set the new password
        user.set_password(new_password)
        user.save()

        return Response({'status': 'success', 'message': 'Password reset successful.'}, status=status.HTTP_200_OK)
