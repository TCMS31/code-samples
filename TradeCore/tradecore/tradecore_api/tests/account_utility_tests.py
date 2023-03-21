"""Unit tests for AccountUtility, with every outbound HTTP call mocked."""

from unittest import mock

import requests
from django.test import SimpleTestCase, TestCase, override_settings

from tradecore_api.tests.factories import UserFactory
from tradecore_api.utils import AccountUtility


class ValidationTests(SimpleTestCase):
    def test_accepts_two_strings(self):
        self.assertTrue(AccountUtility.validate_account_params("a@b.com", "pw"))

    def test_rejects_missing_values(self):
        self.assertFalse(AccountUtility.validate_account_params("", "pw"))
        self.assertFalse(AccountUtility.validate_account_params("a@b.com", ""))

    def test_rejects_non_string_values(self):
        self.assertFalse(AccountUtility.validate_account_params("a@b.com", 1234))
        self.assertFalse(AccountUtility.validate_account_params(None, "pw"))

    def test_post_params_accept_only_like_and_unlike(self):
        self.assertTrue(AccountUtility.validate_post_params("1", "like"))
        self.assertTrue(AccountUtility.validate_post_params("1", "unlike"))
        self.assertFalse(AccountUtility.validate_post_params("1", "delete"))
        self.assertFalse(AccountUtility.validate_post_params(1, "like"))


@override_settings(
    ABSTRACT_GEOLOCATION_API_KEY="",
    ABSTRACT_HOLIDAYS_API_KEY="",
    ABSTRACT_API_TIMEOUT=5,
)
class EnrichmentDisabledTests(SimpleTestCase):
    """With no key configured, no network call may be attempted at all."""

    @mock.patch("tradecore_api.utils.account_utility.session.get")
    def test_geolocation_skips_the_request(self, get_mock):
        self.assertEqual(AccountUtility.get_geolocation_data("8.8.8.8"), {})
        get_mock.assert_not_called()

    @mock.patch("tradecore_api.utils.account_utility.session.get")
    def test_holidays_skips_the_request(self, get_mock):
        self.assertFalse(AccountUtility.get_holiday_data({"country_code": "GB"}))
        get_mock.assert_not_called()


@override_settings(
    ABSTRACT_GEOLOCATION_API_KEY="test-key",
    ABSTRACT_HOLIDAYS_API_KEY="test-key",
    ABSTRACT_API_TIMEOUT=5,
)
class EnrichmentEnabledTests(SimpleTestCase):
    @mock.patch("tradecore_api.utils.account_utility.session.get")
    def test_geolocation_parses_a_successful_response(self, get_mock):
        get_mock.return_value = mock.Mock(
            status_code=200, content=b'{"country_code": "GB"}'
        )
        self.assertEqual(
            AccountUtility.get_geolocation_data("8.8.8.8"), {"country_code": "GB"}
        )

    @mock.patch("tradecore_api.utils.account_utility.session.get")
    def test_geolocation_returns_empty_on_provider_error(self, get_mock):
        get_mock.return_value = mock.Mock(status_code=429, content=b"")
        self.assertEqual(AccountUtility.get_geolocation_data("8.8.8.8"), {})

    @mock.patch("tradecore_api.utils.account_utility.session.get")
    def test_geolocation_survives_a_network_failure(self, get_mock):
        get_mock.side_effect = requests.ConnectionError("offline")
        self.assertEqual(AccountUtility.get_geolocation_data("8.8.8.8"), {})

    @mock.patch("tradecore_api.utils.account_utility.session.get")
    def test_holidays_is_false_without_a_country(self, get_mock):
        self.assertFalse(AccountUtility.get_holiday_data({}))
        get_mock.assert_not_called()

    @mock.patch("tradecore_api.utils.account_utility.session.get")
    def test_holidays_is_true_for_a_non_empty_payload(self, get_mock):
        get_mock.return_value = mock.Mock(status_code=200, content=b'[{"name": "NYD"}]')
        self.assertTrue(AccountUtility.get_holiday_data({"country_code": "GB"}))

    @mock.patch("tradecore_api.utils.account_utility.session.get")
    def test_holidays_is_false_for_an_empty_payload(self, get_mock):
        get_mock.return_value = mock.Mock(status_code=200, content=b"[]")
        self.assertFalse(AccountUtility.get_holiday_data({"country_code": "GB"}))


class TokenTests(TestCase):
    def test_round_trips_a_user(self):
        user = UserFactory.create()
        token = AccountUtility.get_token(user)
        self.assertEqual(AccountUtility.get_user_data(f"JWT {token}"), user)

    def test_rejects_a_missing_header(self):
        self.assertIsNone(AccountUtility.get_user_data(None))
        self.assertIsNone(AccountUtility.get_user_data(""))

    def test_rejects_a_malformed_header(self):
        user = UserFactory.create()
        token = AccountUtility.get_token(user)
        self.assertIsNone(AccountUtility.get_user_data(token))
        self.assertIsNone(AccountUtility.get_user_data(f"Bearer {token}"))

    def test_rejects_a_tampered_token(self):
        user = UserFactory.create()
        token = AccountUtility.get_token(user)
        self.assertIsNone(AccountUtility.get_user_data(f"JWT {token}x"))
