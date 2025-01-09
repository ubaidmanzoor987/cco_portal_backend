import os
import json
import boto3
import subprocess
import tempfile
from PIL import Image
from io import BytesIO
from typing import Optional
from decouple import config
from botocore.exceptions import NoCredentialsError


def initialize_s3_client():
    """
    Initialize and return an S3 client with the configured AWS credentials.
    """
    aws_access_key_id = config('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = config('AWS_SECRET_ACCESS_KEY')
    region_name = config('AWS_REGION')

    return boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name,
        config=boto3.session.Config(signature_version='s3v4')
    )


def set_bucket_policy(s3, bucket_name):
    # Define the bucket policy allowing public read access to all objects
    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*"
            }
        ]
    }

    # Convert the bucket policy to a JSON string
    bucket_policy_str = json.dumps(bucket_policy)

    # Set bucket policy
    s3.put_bucket_policy(Bucket=bucket_name, Policy=bucket_policy_str)


def upload_file_to_s3(file_data):
    try:
        s3 = initialize_s3_client()
        bucket_name = config('S3_BUCKET_NAME')

        # Set bucket policy allowing public read access to all objects
        set_bucket_policy(s3, bucket_name)

        # Upload file to S3 with system-defined metadata
        file_buffer = BytesIO(file_data.read())

        s3.upload_fileobj(
            file_buffer,
            bucket_name,
            file_data.name,
            ExtraArgs={'ContentType': file_data.content_type}
        )
    except NoCredentialsError:
        raise NoCredentialsError('AWS credentials not available.')


def upload_file_to_s3_folder(file_content, file_name, content_type, folder_name):
    """
    Uploads a file to a specified S3 folder. If the file is of a specific extension
    (e.g., .docx, .xlsx, etc.), converts it to an image before uploading and sets the image
    link as the preview link.

    Args:
        file_content (bytes): Content of the file to upload.
        file_name (str): Name of the file to upload.
        content_type (str): MIME type of the file.
        folder_name (str): Folder name in the S3 bucket.

    Returns:
        dict: Dictionary containing preview and download links along with the file name.
    """
    try:
        s3 = initialize_s3_client()
        bucket_name = config('S3_BUCKET_NAME')

        # Set bucket policy allowing public read access to all objects
        set_bucket_policy(s3, bucket_name)

        # Determine the file extension
        file_extension = os.path.splitext(file_name)[1].lower()

        # Ensure the tmp directory exists
        temp_dir = "./tmp"
        os.makedirs(temp_dir, exist_ok=True)

        # Save the file content to a temporary file
        temp_input_path = os.path.join(temp_dir, file_name)
        with open(temp_input_path, "wb") as temp_file:
            temp_file.write(file_content)

        converted_image_path: Optional[str] = None
        converted_image_name: Optional[str] = None

        # Check if the file needs to be converted to an image
        if file_extension in [".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"]:
            converted_image_name = os.path.splitext(file_name)[0] + ".png"
            converted_image_path = convert_file_to_image(temp_input_path, temp_dir)
            if converted_image_path:
                # Optimize the converted image
                with open(converted_image_path, "rb") as img_file:
                    optimized_image = optimize_image(img_file.read())
                if optimized_image:
                    # Save the optimized image to a temporary file
                    with open(converted_image_path, "wb") as opt_file:
                        opt_file.write(optimized_image)

        # Upload the original file
        original_file_key = f"{folder_name}/{file_name}"
        s3.upload_fileobj(
            BytesIO(file_content),
            bucket_name,
            original_file_key,
            ExtraArgs={'ContentType': content_type}
        )
        download_link = f"https://{bucket_name}.s3.amazonaws.com/{original_file_key}"

        # If an image was created, upload it and set its link as the preview link
        if converted_image_path:
            image_file_key = f"{folder_name}/{converted_image_name}"
            with open(converted_image_path, "rb") as image_file:
                s3.upload_fileobj(
                    image_file,
                    bucket_name,
                    image_file_key,
                    ExtraArgs={'ContentType': 'image/png'}
                )
            preview_link = f"https://{bucket_name}.s3.amazonaws.com/{image_file_key}"

            # Clean up the temporary image file
            os.remove(converted_image_path)
        else:
            # If no image conversion was needed, set the original file link as the preview link
            preview_link = f"https://{bucket_name}.s3.amazonaws.com/{original_file_key}"
            download_link = generate_presigned_url(s3, bucket_name, original_file_key, file_name, expiration=3600)

        # Clean up the temporary input file
        os.remove(temp_input_path)

        # Prepare the response object
        resource_s3_file_link = {
            "file_link": {
                "preview_link": preview_link,
                "download_link": download_link
            },
            "file_name": file_name
        }

        return resource_s3_file_link

    except NoCredentialsError:
        raise NoCredentialsError('AWS credentials not available.')
    except Exception as e:
        raise RuntimeError(f"An error occurred while uploading the file: {e}")


def optimize_image(img_data, max_width=120, max_height=1000, quality=100):
    """
    Optimize an image for web use.

    Args:
        img_data (bytes): Raw image data.
        max_width (int): Maximum width of the image.
        max_height (int): Maximum height of the image.
        quality (int): JPEG quality (1-100).

    Returns:
        bytes: Optimized image data in JPEG format.
    """
    try:
        img_temp = tempfile.SpooledTemporaryFile()
        img_temp.write(img_data)
        img_temp.seek(0)

        with Image.open(img_temp) as img:
            # Ensure the file is a valid image
            img.verify()
            img_temp.seek(0)

        with Image.open(img_temp) as img:
            # Convert RGBA to RGB if necessary
            if img.mode == "RGBA":
                img = img.convert("RGB")
            # Resize image
            img.thumbnail((max_width, max_height))
            # Save as optimized JPEG
            output = tempfile.SpooledTemporaryFile()
            img.save(output, format="JPEG", quality=quality, optimize=True)
            output.seek(0)
            return output.read()
    except Exception as e:
        raise RuntimeError(f"Error optimizing image: {e}")


def convert_file_to_image(file_path, temp_dir):
    """
    Converts a file to an image using LibreOffice.

    Args:
        file_path (str): Path to the file to convert.
        temp_dir (str): Temporary directory to save the converted file.

    Returns:
        str: Path to the converted image file.

    Raises:
        RuntimeError: If the conversion fails.
    """
    try:
        # Use LibreOffice in headless mode to convert to PNG
        subprocess.run(
            ['libreoffice', '--headless', '--convert-to', 'png', '--outdir', temp_dir, file_path],
            check=True
        )
        png_files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.endswith('.png')]
        if not png_files:
            raise RuntimeError("No PNG files generated during conversion.")
        return png_files[0]  # Return the first PNG file
    except Exception as e:
        raise RuntimeError(f"Error converting file to image: {e}")


def generate_presigned_url(s3_client, bucket_name, object_key, file_name, expiration=3600):
    """
    Generate a pre-signed URL to share an S3 object for download

    :param s3_client: boto3 S3 client
    :param bucket_name: string
    :param object_key: string
    :param file_name: string
    :param expiration: Time in seconds for the pre-signed URL to remain valid
    :return: Pre-signed URL as string. If error, returns None.
    """
    try:
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key,
                'ResponseContentDisposition': f'attachment; filename="{file_name}"'
            },
            ExpiresIn=expiration
        )
        return response
    except NoCredentialsError:
        print("Credentials not available")
        return None
