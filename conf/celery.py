import os
from celery import Celery
import time


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings")
app = Celery("sria-membership")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# # Add this handler to use Django's logging settings
# logger = get_task_logger(__name__)
# logger.addHandler(settings.CELERY_LOG_HANDLER)


# Your existing Celery tasks
@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


