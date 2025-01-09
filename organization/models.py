from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from datetime import date


# Create your models here.
class Organization(models.Model):
    company_name = models.CharField(max_length=255, unique=True)
    company_number = PhoneNumberField(null=False, blank=False, unique=True)
    company_contact = models.CharField(max_length=255, blank=True, null=True)
    contract_duration = models.IntegerField()
    CONTRACT_PERIODS = [
        ('Weeks', 'Weeks'),
        ('Months', 'Months'),
        ('Years', 'Years'),
    ]

    contract_periods = models.CharField(
        max_length=6,
        choices=CONTRACT_PERIODS,
        default='Weeks',
        blank=False,
    )
    email_address = models.EmailField(blank=False, null=False, unique=True)
    onboarding_date = models.DateField()
    company_address = models.CharField(max_length=512, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    s3_file_link = models.CharField(max_length=255)

    def __str__(self):
        return self.company_name


class BasicTemplate(models.Model):
    name = models.CharField(unique=True, max_length=255)
    basic_html = models.FileField(max_length=255)
    data_json = models.JSONField()

    def __str__(self):
        return self.name
