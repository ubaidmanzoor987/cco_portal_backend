from celery import shared_task
from django.utils import timezone
from .models import CustomUser
import logging

logger = logging.getLogger(__name__)


@shared_task
def set_user_inactive(user_id):
    try:
        logger.info('Starting Schedule Task for Making User Inactive!')
        user = CustomUser.objects.get(pk=user_id)
        user.is_active = False
        user.save()
    except CustomUser.DoesNotExist:
        pass
