import secrets
from datetime import datetime

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import generics, permissions, status
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from core.tasks import send_otp_email_task
from core.utils.otp_generator import get_email_totp
from users.models import User

from .serializers import (
    AddressSerializer,
    OAuthSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)

OTP_TTL_SECONDS = 600  # 10 minutes


class OAuthProviders:
    def __init__(self) -> None:
        self.google_client_id = settings.GOOGLE_CLIENT_ID
        self.github_client_id = settings.GITHUB_CLIENT_ID
        self.facebook_client_id = settings.FACEBOOK_CLIENT_ID

    def verify_google_token(self, token: str) -> dict[str, str | None] | None:
        try:
            print("google client id", self.google_client_id)
            idinfo = id_token.verify_oauth2_token(
                token, google_requests.Request(), self.google_client_id
            )
            print(idinfo)
            return {"name": idinfo.get("name"), "email": idinfo.get("email")}
        except ValueError:
            return None

    def verify_github_token(self, token: str) -> None:
        # Implement GitHub token verification logic here
        pass

    def verify_facebook_token(self, token: str) -> None:
        # Implement Facebook token verification logic here
        pass


class OAuthView(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = OAuthSerializer

    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            return Response(
                {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        token = serializer.validated_data.get("token")
        provider = serializer.validated_data.get("provider")

        if provider != "google":
            return Response(
                {"error": "Unsupported provider"}, status=status.HTTP_400_BAD_REQUEST
            )

        idinfo = OAuthProviders().verify_google_token(token)
        print("idinfo", idinfo)
        if not idinfo or not idinfo.get("email"):
            return Response(
                {"error": "Invalid Google Token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = idinfo["email"]
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"name": idinfo.get("name") or email},
        )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "accessToken": str(refresh.access_token),
                "refreshToken": str(refresh),
                "expires_at": refresh.access_token.payload.get("exp"),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                },
            }
        )


class VerifyEmailView(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        email = request.POST.get("email", "").strip().lower()
        entered_otp = request.POST.get("otp", "").strip()
        cache_key = f"pending_signup_{email}"

        pending = cache.get(cache_key)
        if not pending:
            return Response(
                {"error": "Verification expired. Please sign up again."}, status=status.HTTP_400_BAD_REQUEST
            )

        if pending["attempts"] >= 5:
            cache.delete(cache_key)
            return Response(
                {"error": "Too many failed attempts. Please sign up again."}, status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        if not secrets.compare_digest(pending["otp"], entered_otp):
            pending["attempts"] += 1
            cache.set(cache_key, pending, timeout=OTP_TTL_SECONDS)
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)
        # OTP verified -> now persist the actual User row in PostgreSQL
        user = User(
            username=pending["username"],
            email=pending["email"],
            password=pending["password_hash"],  # Already hashed via make_password
            is_active=True,
        )
        user.save()

        cache.delete(cache_key)

        return Response({"message": "Account created and verified. Please Login."}, status=status.HTTP_201_CREATED)


class ResendOTPView(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request: Request) -> Response:
        email = request.data.get("email")

        if not email:
            return Response(
                {"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Retrieve the pending signup data from the cache
        pending_signup_data = cache.get(f"pending_signup_{email}")

        # wait time
        remaining_time = (
            pending_signup_data.get("wait_time", 0) - datetime.now().timestamp()
            if pending_signup_data
            else 0
        )

        if pending_signup_data and remaining_time > 0:
            wait_time = pending_signup_data["wait_time"]
            if wait_time > 0:
                return Response(
                    {
                        "error": f"Please wait {wait_time} seconds before requesting a new OTP."
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

        # no pending signup found
        if not pending_signup_data:
            return Response(
                {"error": "No pending signup found for this email"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Generate a new OTP code and update the cache
        new_otp_code = get_email_totp(email)
        pending_signup_data["otp_code"] = new_otp_code
        pending_signup_data["wait_time"] = datetime.now().timestamp() + (60**int(
            pending_signup_data.get("retry_count", 0)
        ))  # Increase wait time with each retry
        cache.set(f"pending_signup_{email}", pending_signup_data)

        # Send the new OTP code via email (using Celery task)
        send_otp_email_task.delay(email, new_otp_code)

        return Response(
            {"message": "New OTP code sent to your email"},
            status=status.HTTP_200_OK,
        )


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = (permissions.AllowAny,)

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data()
        hashed_password = make_password(data["password"])

        # Save the user data in the cache for later verification
        cache.set(
            f"pending_signup_{data['email']}",
            {
                "name": data["name"],
                "email": data["email"],
                "password": hashed_password,
                "otp_code": get_email_totp(data["email"]),
                "wait_time": datetime.now().timestamp()
                + 60,  # 1 minute wait time before resending OTP
                "retry_count": 0,  # Track the number of OTP resend attempts
            },
        )

        return Response(
            {
                "message": "User registered successfully. Please check your email for the verification code."
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    serializer_class = TokenObtainPairSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response(
                {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
            )

        user = serializer.user
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "accessToken": str(refresh.access_token),
                "refreshToken": str(refresh),
                "expires_at": refresh.access_token.payload.get("exp"),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                },
            }
        )


class TokenRefreshView(TokenObtainPairView):
    serializer_class = TokenObtainPairSerializer
    permission_classes = (AllowAny,)

    def post(self, request: Request, *args, **kwargs) -> Response:
        refresh_token = request.data.get("refreshToken")

        if not refresh_token:
            return Response(
                {"error": "Refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh = RefreshToken(refresh_token)

            ## get the user  and blacklist the old refresh token
            loggedin_user = User.objects.get(id=refresh.payload.get("user_id"))
            refresh_user_token = RefreshToken.for_user(loggedin_user)

            # new tokens
            refresh_token = str(refresh_user_token)
            access_token = str(refresh_user_token.access_token)
            expires_at = refresh_user_token.access_token.payload.get("exp")
        except Exception as e:
            return Response(
                {"error": f"Invalid refresh token {e}"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(
            {
                "accessToken": access_token,
                "refreshToken": str(refresh_token),
                "expires_at": expires_at,
            }
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self) -> User:
        return self.request.user


class AddressListView(GenericViewSet, ListModelMixin, CreateModelMixin):
    serializer_class = AddressSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return self.request.user.addresses.all()
