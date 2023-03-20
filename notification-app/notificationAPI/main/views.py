"""Read the notification log and post new messages.

``Log`` rows are always fetched with their related user, message, category and
channel. Both log serializers reach through every one of those relations, so
without ``select_related`` a page of 50 rows costs 200+ extra queries.
"""

from braces.views import CsrfExemptMixin
from rest_framework.generics import CreateAPIView, ListAPIView

from .models import Log, MessageCategories
from .serializers import (
    LogSerializer,
    LogStringSerializer,
    MessageCategorySerializer,
    MessageSerializer,
)


class LogQuerySetMixin:
    """Shared, fully-joined queryset for the log endpoints."""

    def get_queryset(self):
        return Log.objects.select_related(
            "user", "channel", "message__category"
        ).order_by("-created_on")


class LogStringListView(LogQuerySetMixin, CsrfExemptMixin, ListAPIView):
    """Human-readable one-line rendering of each log entry."""

    serializer_class = LogStringSerializer


class LogListView(LogQuerySetMixin, CsrfExemptMixin, ListAPIView):
    """Structured log entries with their related objects expanded."""

    serializer_class = LogSerializer


class CreateMessageAPIView(CsrfExemptMixin, CreateAPIView):
    """Create a message, which fans out notifications to every channel."""

    serializer_class = MessageSerializer


class MessageCategoryListView(ListAPIView):
    """List the available message categories.

    The front-end used to hardcode category ids 1/2/3, which silently pointed at
    the wrong rows in any database where the categories were created in a
    different order.
    """

    serializer_class = MessageCategorySerializer
    queryset = MessageCategories.objects.all().order_by("name")
    pagination_class = None
