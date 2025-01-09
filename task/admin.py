from django.contrib import admin
from .models import Task, TaskHistory, DeletedTaskHistory, OrganizationTask, OrganizationUserTask


# ✅ Task Admin
class TaskAdmin(admin.ModelAdmin):
    readonly_fields = ('task_uuid', 'schedule_date', 'frequency', 'created_at')
    list_display = ('task_uuid', 'task_title', 'frequency', 'due_date', 'task_status', 'assigned_by')
    fields = ('task_uuid', 'task_title', 'manual_reference', 'schedule_date', 'due_date', 'additional_tags',
              'overview', 'answer_data', 'frequency', 'frequency_due_date', 's3_file_links',
              'resource_file_s3_links', 'template_json_data', 'task_status', 'user_list', 'task_report_link',
              'frequency_period', 'task_history', 'created_by', 'updated_by', 'created_at', 'assigned_by')


#  TaskHistory Admin
class TaskHistoryAdmin(admin.ModelAdmin):
    list_display = ('id',)
    fields = ('changes_data',)
    readonly_fields = ('id',)


# DeletedTaskHistory Admin
class DeletedTaskHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'reason_for_deletion', 'deleted_at', 'deleted_by', 'organization')
    fields = ('task_data', 'task_history', 'reason_for_deletion', 'deleted_at', 'deleted_by', 'organization')
    readonly_fields = ('deleted_at',)


# OrganizationTask Admin
class OrganizationTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'organization', 'task')
    fields = ('organization', 'task')
    readonly_fields = ('id',)


#  OrganizationUserTask Admin
class OrganizationUserTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'organization', 'organization_user', 'task')
    fields = ('organization', 'organization_user', 'task')
    readonly_fields = ('id',)


# Registering Admin Classes
admin.site.register(Task, TaskAdmin)
admin.site.register(TaskHistory, TaskHistoryAdmin)
admin.site.register(DeletedTaskHistory, DeletedTaskHistoryAdmin)
admin.site.register(OrganizationTask, OrganizationTaskAdmin)
admin.site.register(OrganizationUserTask, OrganizationUserTaskAdmin)

