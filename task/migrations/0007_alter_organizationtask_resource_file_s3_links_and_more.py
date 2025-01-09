from django.db import migrations, models


def convert_to_json(apps, schema_editor):
    OrganizationTask = apps.get_model('task', 'OrganizationTask')
    OrganizationUserTask = apps.get_model('task', 'OrganizationUserTask')

    # Convert resource_file_s3_links from ArrayField to JSONField
    for task in OrganizationTask.objects.all():
        task.resource_file_s3_links = [item for item in task.resource_file_s3_links]
        task.save()

    for user_task in OrganizationUserTask.objects.all():
        user_task.resource_file_s3_links = [item for item in user_task.resource_file_s3_links]
        user_task.save()


class Migration(migrations.Migration):
    dependencies = [
        ('task', '0006_task_frequency_due_date_alter_task_due_date'),  # Replace with your previous migration
    ]

    operations = [
        # Remove the old ArrayField first (optional if you've already truncated the tables)
        migrations.RemoveField(
            model_name='organizationtask',
            name='resource_file_s3_links',
        ),
        migrations.RemoveField(
            model_name='organizationusertask',
            name='resource_file_s3_links',
        ),
        # Add the new JSONField
        migrations.AddField(
            model_name='organizationtask',
            name='resource_file_s3_links',
            field=models.JSONField(default=list, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='organizationusertask',
            name='resource_file_s3_links',
            field=models.JSONField(default=list, blank=True, null=True),
        ),
        # Perform data migration
        migrations.RunPython(convert_to_json),
    ]
