import os
from .models import Task
from celery import shared_task
from django.db.models import Q
from utils.s3_utils import initialize_s3_client, generate_presigned_url

# Define allowed extensions for files that need the download link updated
ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.pdf']


def is_image_or_pdf(file_name):
    """
    Helper function to check if the file is an image or PDF based on its extension.
    """
    # Get the file extension in lowercase
    file_extension = os.path.splitext(file_name)[1].lower()
    return file_extension in ALLOWED_EXTENSIONS


@shared_task
def update_download_links():
    s3_client = initialize_s3_client()
    bucket_name = os.environ.get('S3_BUCKET_NAME')

    def update_links(tasks):
        print("Inside update_links function")

        for task in tasks:
            print(f"task_id: {task.id}")
            # Update resource_file_s3_links
            if task.resource_file_s3_links:
                updated_resource_links = []
                for file_info in task.resource_file_s3_links:
                    object_key = file_info['file_link']['preview_link'].split(f"{bucket_name}.s3.amazonaws.com/")[1]
                    file_name = file_info['file_name']
                    new_download_link = generate_presigned_url(s3_client, bucket_name, object_key, file_name)
                    print(f"Updating resource link: {file_info['file_link']['download_link']} -> {new_download_link}")
                    file_info['file_link']['download_link'] = new_download_link
                    updated_resource_links.append(file_info)
                task.resource_file_s3_links = updated_resource_links

            # Update s3_file_links
            if task.s3_file_links:
                updated_s3_links = []

                for file_info in task.s3_file_links:
                    # Unwrap the file_info dictionary to get the file details
                    for file_key, file_data in file_info.items():
                        file_name = file_data['file_name']
                        file_link = file_data['file_link']

                        # Check if the file extension is in our allowed list (image or pdf)
                        if is_image_or_pdf(file_name):
                            object_key = file_link['preview_link'].split(f"{bucket_name}.s3.amazonaws.com/")[1]
                            new_download_link = generate_presigned_url(s3_client, bucket_name, object_key, file_name)
                            print(f"Updating s3 file link: {file_link['download_link']} -> {new_download_link}")

                            # Update the download link
                            file_link['download_link'] = new_download_link

                        # Append the updated file_info
                        updated_s3_links.append({file_key: file_data})

                # Assign the updated s3_file_links back to the task
                task.s3_file_links = updated_s3_links

            # Update task_report_link
            if task.task_report_link:
                updated_report_links = []
                for file_info in task.task_report_link:
                    object_key = file_info['file_link']['preview_link'].split(f"{bucket_name}.s3.amazonaws.com/")[1]
                    file_name = file_info['file_name']
                    new_download_link = generate_presigned_url(s3_client, bucket_name, object_key, file_name)
                    print(f"Updating report link: {file_info['file_link']['download_link']} -> {new_download_link}")
                    file_info['file_link']['download_link'] = new_download_link
                    updated_report_links.append(file_info)
                task.task_report_link = updated_report_links

            # Save the updated task
            task.save()

    print("Inside update_download_links function")
    # Fetch all tasks that need their download links updated
    tasks = Task.objects.filter(
        Q(s3_file_links__isnull=False) |
        Q(resource_file_s3_links__isnull=False) |
        Q(task_report_link__isnull=False)
    )
    print(f"total_tasks: {len(tasks)}")
    update_links(tasks)
