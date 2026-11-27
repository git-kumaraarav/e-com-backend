from unittest.mock import Mock, patch

from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class LoginViewTests(APITestCase):
    def setUp(self) -> None:
        self.password = "strong-password-123"
        self.user = User.objects.create_user(
            email="alice@example.com",
            name="Alice",
            password=self.password,
        )

    def test_login_returns_access_and_refresh_tokens(self) -> None:
        response = self.client.post(
            "/api/auth/login/",
            {"email": "alice@example.com", "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("accessToken", response.data)
        self.assertIn("refreshToken", response.data)

    def test_login_rejects_invalid_credentials(self) -> None:
        response = self.client.post(
            "/api/auth/login/",
            {"email": "alice@example.com", "password": "wrong-password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class RegistrationOTPTests(APITestCase):
    def setUp(self) -> None:
        cache.clear()

    @patch("users.views.send_otp_email_task.delay")
    def test_registration_and_email_verification_create_user(
        self, send_email: Mock
    ) -> None:
        response = self.client.post(
            "/api/auth/register/",
            {
                "name": "New User",
                "email": "new@example.com",
                "password": "strong-password-123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        send_email.assert_called_once()
        pending = cache.get("pending_signup_new@example.com")

        response = self.client.post(
            "/api/auth/verify-email/",
            {"email": "new@example.com", "otp": pending["otp"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="new@example.com")
        self.assertEqual(user.name, "New User")
        self.assertTrue(user.check_password("strong-password-123"))

    @patch("users.views.send_otp_email_task.delay")
    def test_resend_otp_updates_pending_code_after_cooldown(
        self, send_email: Mock
    ) -> None:
        self.client.post(
            "/api/auth/register/",
            {
                "name": "New User",
                "email": "new@example.com",
                "password": "strong-password-123",
            },
            format="json",
        )
        pending = cache.get("pending_signup_new@example.com")
        pending["wait_time"] = 0
        cache.set("pending_signup_new@example.com", pending, timeout=600)

        response = self.client.post(
            "/api/auth/resend-otp/",
            {"email": "new@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        send_email.assert_called_with("new@example.com", pending["otp"])
        self.assertEqual(
            cache.get("pending_signup_new@example.com")["otp"], pending["otp"]
        )


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class PasswordResetOTPTests(APITestCase):
    def setUp(self) -> None:
        cache.clear()
        self.user = User.objects.create_user(
            email="reset@example.com",
            name="Reset User",
            password="strong-password-123",
        )

    @patch("users.views.send_otp_email_task.delay")
    def test_password_reset_otp_can_be_resent(self, send_email: Mock) -> None:
        response = self.client.post(
            "/api/auth/forgot-password/",
            {"email": self.user.email},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pending = cache.get("reset_password_reset@example.com")
        self.assertEqual(pending["name"], self.user.name)

        pending["wait_time"] = 0
        cache.set("reset_password_reset@example.com", pending, timeout=300)
        response = self.client.post(
            "/api/auth/resend-otp/",
            {"email": self.user.email},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        send_email.assert_called_with(
            self.user.email, pending["otp"], self.user.name
        )
        self.assertEqual(
            cache.get("reset_password_reset@example.com")["otp"], pending["otp"]
        )
