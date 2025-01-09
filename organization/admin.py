from django.contrib import admin
from .models import *


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'company_number', 'company_address', 'onboarding_date', 'description']


@admin.register(BasicTemplate)
class FileUploadAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'basic_html', 'data_json'
    )
