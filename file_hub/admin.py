from django.contrib import admin
from .models import FileUpload


@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    list_display = (
        'date', 'title', 'description', 's3_file_link'
    )  # Customize the fields you want to display in the admin list view
    search_fields = ('title', 'description')  # Add fields to be searchable in the admin interface
