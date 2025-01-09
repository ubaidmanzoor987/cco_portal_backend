from django.db import models
from django.contrib.auth.models import (
    PermissionsMixin,
    AbstractBaseUser,
    BaseUserManager,
)
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Permission

from organization.models import Organization
from phonenumber_field.modelfields import PhoneNumberField


class UserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    def create_user(self, email, password, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError(_("The Email must be set"))
        extra_fields.setdefault("is_staff", False)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        # Assign the user to the 'organization' group

        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_("email address"), unique=True)
    username = models.CharField(max_length=30, blank=True, null=True)
    first_name = models.CharField(_("First Name"), max_length=50, blank=True, null=True)
    last_name = models.CharField(_("Last Name"), max_length=50, blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True,
                                     null=True)
    number = PhoneNumberField(blank=True, null=True, unique=True)
    active_duration = models.IntegerField(blank=True, null=True)
    ACTIVE_PERIODS = [
        ('Hours', 'Hours'),
        ('Months', 'Months'),
        ('Years', 'Years'),
    ]

    active_periods = models.CharField(
        max_length=6,
        choices=ACTIVE_PERIODS,
        default='Weeks',
        blank=False,
    )

    ROLE_CHOICES = [
        ('CCO', 'CCO'),
        ('Advisor', 'Advisor'),
    ]

    role = models.CharField(
        max_length=7,
        choices=ROLE_CHOICES,
        default='CCO',
    )
    description = models.TextField(blank=True, null=True)
    is_staff = models.BooleanField(default=False)
    groups = models.ManyToManyField(
        Group, verbose_name=_('groups'), blank=True, related_name='customuser_set',
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.'
    )
    user_permissions = models.ManyToManyField(
        Permission, verbose_name=_('user permissions'), blank=True, related_name='customuser_set',
        help_text='Specific permissions for this user.'
    )
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(_("date joined"), auto_now_add=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)
    about_me = models.TextField(blank=True, null=True)
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    gender = models.CharField(_("gender"), max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    s3_image_link = models.CharField(max_length=255, blank=True, null=True)
    celery_task_id = models.CharField(_("Celery Task ID"), max_length=100, blank=True, null=True)
    created_with_org = models.BooleanField(default=True, blank=True, null=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    def __str__(self):
        return self.email
