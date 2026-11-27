from rest_framework import serializers

from .models import Address, User


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        """Username is the email address, and it must be unique."""

        model = User
        fields = ("id", "name",  "email", "password")

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("email", "name")


class UserProfileExtendedSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    class Meta:
        model = UserProfileSerializer
        fields = "__all__"
    
class AddressSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    class Meta:
        model = Address  
        fields = ("__all__")


class OAuthSerializer(serializers.Serializer):
    token = serializers.CharField()
    provider = serializers.ChoiceField(choices=["google", "github", "facebook"])
    
class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

class VerifyEmailSerializer(EmailSerializer):
    otp = serializers.CharField(max_length=6, min_length=6)

class ResendOTPSerializer(EmailSerializer):
    pass 

class ResetPasswordSerializer(EmailSerializer):
    otp = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)
