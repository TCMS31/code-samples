from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from tradecore_api.serializers import UserSerializer
from tradecore_api.utils import AccountUtility


class SignUpAPIView(APIView):
    """Create a new user account."""

    permission_classes = (AllowAny,)

    @staticmethod
    def _client_ip(request):
        """Prefer the left-most X-Forwarded-For entry, else REMOTE_ADDR."""
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    def post(self, request):
        """Validate the payload, enrich it where possible and create the user."""
        payload = dict(request.data)

        geolocation_data = AccountUtility.get_geolocation_data(self._client_ip(request))
        payload["geolocation_data"] = geolocation_data
        payload["joined_on_holiday"] = AccountUtility.get_holiday_data(geolocation_data)

        serializer = UserSerializer(data=payload)
        if not serializer.is_valid():
            return Response(
                {"validation_error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(payload.get("password"))
        except DjangoValidationError as err:
            return Response(
                {"validation_error": {"password": list(err.messages)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
