import os

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import generics, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import IsAuthenticated, AllowAny     

from users.models import User

from .serializers import OAuthSerializer, UserProfileSerializer, UserRegistrationSerializer
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file


class OAuthProviders:
    def __init__(self) -> None:
        self.google_client_id = os.environ.get("GOOGLE_CLIENT_ID")
        self.github_client_id = os.environ.get("GITHUB_CLIENT_ID")
        self.facebook_client_id = os.environ.get("FACEBOOK_CLIENT_ID")

    def verify_google_token(
        self, token: str
    ) -> dict[str, str | None] | None:
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


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = (permissions.AllowAny,)


class LoginView(TokenObtainPairView):
    serializer_class = TokenObtainPairSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
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
    permission_classes = (AllowAny, )

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
                {"error": f"Invalid refresh token {e}"}, status=status.HTTP_401_UNAUTHORIZED
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
        print(self.request.user)
        return self.request.user
