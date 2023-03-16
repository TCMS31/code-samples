from unittest import mock

from django.contrib.auth.hashers import check_password
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from tradecore_api.models import User
from tradecore_api.tests.factories import DEFAULT_PASSWORD, UserFactory


class LoginTests(APITestCase):
    """Cover the /api/login endpoint."""

    def test_login_with_valid_creds_returns_token(self):
        user = UserFactory.create()
        response = self.client.post(
            reverse("login"),
            data={"email": user.email, "password": DEFAULT_PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # A token must actually come back, and it must identify this user.
        self.assertTrue(response.data["token"])
        self.assertEqual(response.data["user"]["email"], user.email)
        # The password must never be echoed back.
        self.assertNotIn("password", response.data["user"])

    def test_login_stamps_authentication_time(self):
        user = UserFactory.create()
        self.assertIsNone(user.token_authenticated_at)
        self.client.post(
            reverse("login"),
            data={"email": user.email, "password": DEFAULT_PASSWORD},
            format="json",
        )
        user.refresh_from_db()
        self.assertIsNotNone(user.token_authenticated_at)

    def test_login_is_case_insensitive_on_email(self):
        user = UserFactory.create()
        response = self.client.post(
            reverse("login"),
            data={"email": user.email.upper(), "password": DEFAULT_PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_with_invalid_creds(self):
        user = UserFactory.create()
        response = self.client.post(
            reverse("login"),
            data={"email": user.email, "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("token", response.data)

    def test_login_with_missing_email_param(self):
        response = self.client.post(
            reverse("login"), data={"user": "abc", "password": "123"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_with_non_string_password(self):
        response = self.client.post(
            reverse("login"),
            data={"email": "a@example.com", "password": 12345},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserCreationTests(APITestCase):
    """Cover the User model, its manager and the /api/signup endpoint."""

    def test_factory_stores_a_hashed_password(self):
        """Regression: the factory used to write the password in plain text."""
        user = UserFactory.create()
        self.assertNotEqual(user.password, DEFAULT_PASSWORD)
        self.assertTrue(check_password(DEFAULT_PASSWORD, user.password))

    def test_manager_lowercases_email(self):
        user = User.objects.create_user(
            email="MiXeD@Example.COM",
            password=DEFAULT_PASSWORD,
            first_name="A",
            last_name="B",
        )
        self.assertEqual(user.email, "mixed@example.com")

    def test_signup_succeeds_without_any_enrichment_api_key(self):
        """Regression: signup used to 400 whenever the Abstract API key was absent.

        ``geolocation_data`` had no default, so the empty dict returned by the
        unauthenticated lookup failed model validation.
        """
        data = {
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@example.com",
            "password": "a-Strong-passw0rd",
        }
        response = self.client.post(reverse("signup"), data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["geolocation_data"], {})
        self.assertFalse(response.data["joined_on_holiday"])
        self.assertTrue(User.objects.filter(email="ada@example.com").exists())

    def test_signup_hashes_the_password(self):
        data = {
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada2@example.com",
            "password": "a-Strong-passw0rd",
        }
        self.client.post(reverse("signup"), data=data, format="json")
        user = User.objects.get(email="ada2@example.com")
        self.assertTrue(check_password("a-Strong-passw0rd", user.password))

    @mock.patch("tradecore_api.utils.account_utility.AccountUtility.get_holiday_data")
    @mock.patch(
        "tradecore_api.utils.account_utility.AccountUtility.get_geolocation_data"
    )
    def test_signup_stores_enrichment_when_available(self, geo_mock, holiday_mock):
        """The enrichment providers are mocked — no test makes a real API call."""
        geo_mock.return_value = {"country_code": "GB", "city": "London"}
        holiday_mock.return_value = True

        data = {
            "first_name": "Alan",
            "last_name": "Turing",
            "email": "alan@example.com",
            "password": "a-Strong-passw0rd",
        }
        response = self.client.post(reverse("signup"), data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["geolocation_data"]["city"], "London")
        self.assertTrue(response.data["joined_on_holiday"])

    def test_signup_rejects_non_string_first_name(self):
        data = {
            "first_name": {"not": "a string"},
            "last_name": "Lovelace",
            "email": "bad@example.com",
            "password": "a-Strong-passw0rd",
        }
        response = self.client.post(reverse("signup"), data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup_rejects_weak_password(self):
        data = {
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "weak@example.com",
            "password": "12345",
        }
        response = self.client.post(reverse("signup"), data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data["validation_error"])

    def test_signup_rejects_duplicate_email(self):
        UserFactory.create(email="dupe@example.com")
        data = {
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "dupe@example.com",
            "password": "a-Strong-passw0rd",
        }
        response = self.client.post(reverse("signup"), data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserDetailTests(APITestCase):
    """Cover the /api/user/<id> endpoint."""

    def test_returns_user_for_known_id(self):
        user = UserFactory.create()
        response = self.client.get(reverse("user", kwargs={"id": user.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["email"], user.email)

    def test_returns_404_for_unknown_id(self):
        response = self.client.get(reverse("user", kwargs={"id": 999999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
