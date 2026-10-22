from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase


class LoginViewTests(APITestCase):
    def setUp(self) -> None:
        self.password = "strong-password-123"
        User.objects.create_user(username="alice", password=self.password)

    def test_login_returns_access_and_refresh_tokens(self) -> None:
        response = self.client.post(
            "/api/auth/login/",
            {"username": "alice", "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_rejects_invalid_credentials(self) -> None:
        response = self.client.post(
            "/api/auth/login/",
            {"username": "alice", "password": "wrong-password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
