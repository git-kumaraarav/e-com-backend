from math import ceil

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
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
    EmailSerializer,
    OAuthSerializer,
    ResendOTPSerializer,
    ResetPasswordSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
    VerifyEmailSerializer,
)

OTP_TTL_SECONDS = 300  # 5 minutes in seconds


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
    serializer_class = VerifyEmailSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        entered_otp = serializer.validated_data["otp"]

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

        totp = get_email_totp(email)

        # valid_window=1 accepts the current 5-minute window and minor boundary drift
        if not totp.verify(entered_otp, valid_window=4):
            pending["attempts"] += 1
            cache.set(cache_key, pending, timeout=OTP_TTL_SECONDS + 60)
            return Response({"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)

        # OTP verified -> now persist the actual User row in PostgreSQL
        user = User(
            email=pending["email"],
            name=pending["name"],
            password=pending["password_hash"],  # Already hashed via make_password
            is_active=True,
        )
        user.save()

        # Send the OTP email asynchronously using Celery
        transaction.on_commit(
            lambda: send_otp_email_task.delay(email, entered_otp, pending["name"])
        )

        cache.delete(cache_key)

        return Response({"message": "Account created and verified. Please Login."}, status=status.HTTP_201_CREATED)


class ResendOTPView(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = ResendOTPSerializer

    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        cache_key = f"pending_signup_{email}"
        pending_otp_request = cache.get(cache_key)
        is_password_reset = False
        if not pending_otp_request:
            cache_key = f"reset_password_{email}"
            pending_otp_request = cache.get(cache_key)
            is_password_reset = True

        if not pending_otp_request:
            return Response(
                {"error": "No pending OTP request found for this email"},
                status=status.HTTP_404_NOT_FOUND,
            )

        now = timezone.now().timestamp()
        remaining_time = ceil(pending_otp_request.get("wait_time", 0) - now)
        if remaining_time > 0:
            return Response(
                {"error": f"Please wait {remaining_time} seconds before requesting a new OTP."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        new_otp_code = get_email_totp(email).now()
        retry_count = pending_otp_request.get("retry_count", 0)
        pending_otp_request["otp"] = new_otp_code
        pending_otp_request["retry_count"] = retry_count + 1
        pending_otp_request["wait_time"] = now + 60 * (2**retry_count)
        cache.set(
            cache_key,
            pending_otp_request,
            timeout=OTP_TTL_SECONDS,
        )
        if is_password_reset:
            send_otp_email_task.delay(
                email, new_otp_code, pending_otp_request.get("name", "")
            )
        else:
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

        # validate incoming 
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        hashed_password = make_password(data["password"])
        email = data["email"]

        # generate OTP 
        otp_code = get_email_totp(email).now()

        # cache user data for 5 minutes (300 seconds) with a unique key
        cache.set(
            f"pending_signup_{email}",
            {
                "name": data["name"],
                "email": email,
                "password_hash": hashed_password,
                "otp": otp_code,
                "attempts": 0,
                "wait_time": timezone.now().timestamp() + 60,
                "retry_count": 0,
            },
            timeout=OTP_TTL_SECONDS,
        )
        # Send the OTP email asynchronously using Celery
        send_otp_email_task.delay(email, otp_code, data["name"])

        return Response(
            {
                "message": "Please check your email for the verification code."
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


class ForgetPasswordRequest(generics.GenericAPIView):
    serializer_class = EmailSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "User with this email does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        otp_code = get_email_totp(email).now()

        cache.set(
            f"reset_password_{email}",
            {
                "otp": otp_code,
                "attempts": 0,
                "wait_time": timezone.now().timestamp() + 60,
                "retry_count": 0,
                "name": user.name,
            },
            timeout=OTP_TTL_SECONDS,
        )
        send_otp_email_task.delay(email, otp_code, user.name)

        return Response(
            {"message": "Please check your email for the verification code."},
            status=status.HTTP_200_OK,
        )
        

class ResetPassword(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request: Request, *args, **kwargs) -> Response:
        # 1. GET the email, otp and new password from the request
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]
        new_password = serializer.validated_data["new_password"]

        # 2. Verify the OTP using the get_email_totp function
        totp = get_email_totp(email)
        if not totp.verify(otp, valid_window=4):
            return Response(
                {"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST
            )

        # 3. If OTP is valid, update the user's password with the new password
        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
        except User.DoesNotExist:
            return Response(
                {"error": "User with this email does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {"message": "Password reset successfully."},
            status=status.HTTP_200_OK,
        )