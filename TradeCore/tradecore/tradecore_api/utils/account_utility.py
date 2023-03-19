"""Account helpers: parameter validation, optional signup enrichment, JWT issuing.

The two Abstract API lookups used at signup are *optional enrichment*. When no
API key is configured the lookup is skipped entirely — no network call is made
and signup still succeeds with empty geolocation data. That keeps a fresh clone
(and the test suite) working without a paid third-party account.
"""

import datetime
import json
import logging
import os

import jwt
import requests
from django.conf import settings
from rest_framework_jwt.utils import jwt_payload_handler

from tradecore_api.models import Post, User

logger = logging.getLogger(__name__)

DEFAULT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux i686; rv:64.0) Gecko/20100101 Firefox/64.0",
    "Accept-Encoding": "br, gzip, deflate",
    "Accept": "*/*",
    "Connection": "keep-alive",
}
MAX_RETRIES = 3
JWT_ALGORITHM = "HS256"

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(max_retries=MAX_RETRIES)
session.mount("https://", adapter)
session.mount("http://", adapter)


def _jwt_secret():
    """Signing key for the API's own tokens, falling back to Django's SECRET_KEY."""
    return os.environ.get("SECRET_KEY") or settings.SECRET_KEY


class AccountUtility:
    """Helpers for user accounts: validation, enrichment and token handling."""

    @classmethod
    def validate_account_params(cls, email, password):
        """Return True when email and password are both non-empty strings."""
        if not email or not password:
            return False
        return isinstance(email, str) and isinstance(password, str)

    @classmethod
    def validate_post_params(cls, post_id, action):
        """Return True when post_id is a non-empty string and action is like/unlike."""
        if not post_id or not isinstance(post_id, str):
            return False
        return isinstance(action, str) and action in ("like", "unlike")

    @classmethod
    def get_geolocation_data(cls, ip):
        """Look up geolocation for an IP.

        Returns {} when no API key is configured, when the IP is missing, or when
        the provider is unreachable. Never raises.
        """
        api_key = getattr(settings, "ABSTRACT_GEOLOCATION_API_KEY", "")
        if not api_key or not ip:
            return {}

        url = (
            "https://ipgeolocation.abstractapi.com/v1/"
            f"?api_key={api_key}&ip_address={ip}"
        )
        try:
            response = session.get(
                url,
                headers=DEFAULT_REQUEST_HEADERS,
                timeout=settings.ABSTRACT_API_TIMEOUT,
            )
        except requests.RequestException:
            logger.warning("Geolocation lookup failed; continuing without it.")
            return {}

        if response.status_code != 200:
            return {}
        try:
            return json.loads(response.content)
        except ValueError:
            return {}

    @classmethod
    def get_holiday_data(cls, geolocation_data):
        """Return True when the signup date is a public holiday in the user's country.

        Returns False when no API key is configured or the country is unknown.
        Never raises.
        """
        api_key = getattr(settings, "ABSTRACT_HOLIDAYS_API_KEY", "")
        country = (geolocation_data or {}).get("country_code")
        if not api_key or not country:
            return False

        today = datetime.date.today()
        url = (
            "https://holidays.abstractapi.com/v1/"
            f"?api_key={api_key}&country={country}"
            f"&year={today.year}&month={today.month}&day={today.day}"
        )
        try:
            response = session.get(
                url,
                headers=DEFAULT_REQUEST_HEADERS,
                timeout=settings.ABSTRACT_API_TIMEOUT,
            )
        except requests.RequestException:
            logger.warning("Holiday lookup failed; continuing without it.")
            return False

        if response.status_code != 200:
            return False
        try:
            return bool(json.loads(response.content))
        except ValueError:
            return False

    @classmethod
    def get_token(cls, user):
        """Return a signed JWT for the given user as a ``str``.

        PyJWT 1.x returns ``bytes`` from ``encode`` while 2.x returns ``str``.
        Normalising here keeps callers (and the JSON response) independent of
        which version is installed.
        """
        payload = jwt_payload_handler(user)
        token = jwt.encode(payload, _jwt_secret())
        return token.decode("utf-8") if isinstance(token, bytes) else token

    @classmethod
    def get_user_data(cls, authorization_header):
        """Resolve an ``Authorization: JWT <token>`` header to a User, or None."""
        if not authorization_header or not isinstance(authorization_header, str):
            return None
        parts = authorization_header.split()
        if len(parts) != 2 or parts[0].upper() != "JWT":
            return None
        try:
            user_data = jwt.decode(parts[1], _jwt_secret())
            return User.objects.get(email=user_data["email"])
        except (jwt.InvalidTokenError, User.DoesNotExist, KeyError):
            return None

    @classmethod
    def check_post_authorization(cls, user, post_id):
        """Return True when the post exists and belongs to the given user."""
        try:
            return Post.objects.get(id=post_id).user_id == user.id
        except Post.DoesNotExist:
            return False
