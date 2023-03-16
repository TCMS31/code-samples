from django.db import models, transaction

from .notifications import NotificationDispatcher


class MessageManager(models.Manager):
    """Creating a Message fans notifications out to every registered channel."""

    def create(self, *args, **kwargs):
        # The message and all of its log rows land together, so a failing
        # dispatcher cannot leave a message with a half-written audit trail.
        with transaction.atomic():
            message = super().create(*args, **kwargs)
            if message.category_id:
                for dispatcher in NotificationDispatcher.dispatchers():
                    dispatcher().send_notification(message)
            return message
