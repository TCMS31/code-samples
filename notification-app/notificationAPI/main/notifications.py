"""Notification dispatch.

Extension point: subclass ``NotificationDispatcher``, set ``channel_name`` to a
value present in ``Channel.channel_choices``, and the new channel is picked up
automatically the next time a message is created. No registration call and no
change to the manager is needed.

``dispatchers()`` walks the subclass tree recursively, so a dispatcher that
extends another dispatcher (for example an SMS subclass for a second provider)
is still found.
"""

import logging

from django.apps import apps

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Base dispatcher: writes one Log row per subscribed user."""

    #: Must match a Channel.name value. Subclasses set this.
    channel_name = None

    @classmethod
    def dispatchers(cls):
        """Return every concrete dispatcher subclass, depth-first."""
        found = []
        for subclass in cls.__subclasses__():
            if subclass.channel_name:
                found.append(subclass)
            found.extend(subclass.dispatchers())
        return found

    def recipients(self, message, channel_obj):
        """Users subscribed to both this channel and the message's category."""
        return channel_obj.subscribers.all() & message.category.subscribers.all()

    def send_notification(self, message, channel=None):
        """Deliver ``message`` over this dispatcher's channel.

        Returns True when the channel exists, False when it is not configured.
        """
        channel_model = apps.get_model("main.Channel")
        log_model = apps.get_model("main.Log")
        name = channel or self.channel_name

        try:
            channel_obj = channel_model.objects.get(name=name)
        except channel_model.DoesNotExist:
            logger.warning("Channel %r is not configured; skipping.", name)
            return False

        # One bulk insert rather than a save per recipient.
        log_model.objects.bulk_create(
            [
                log_model(user=user, message=message, channel=channel_obj)
                for user in self.recipients(message, channel_obj)
            ]
        )
        return True


class SMSNotificationDispatcher(NotificationDispatcher):
    """Send notifications over SMS."""

    channel_name = "SMS"


class PushNotificationDispatcher(NotificationDispatcher):
    """Send push notifications."""

    channel_name = "Push Notification"


class EmailNotificationDispatcher(NotificationDispatcher):
    """Send notifications over e-mail."""

    channel_name = "E-Mail"
