from django.db import models


# Create your models here.
class FileUpload(models.Model):
    date = models.DateField()
    title = models.CharField(max_length=255)
    description = models.TextField()
    s3_file_link = models.CharField(max_length=255)

    def __str__(self):
        return self.title
