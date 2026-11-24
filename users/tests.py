from django.contrib.auth import get_user_model
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
