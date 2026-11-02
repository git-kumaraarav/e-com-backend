from rest_framework import serializers
from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        """Username is the email address, and it must be unique."""

        model = User
        fields = ("id", "name",  "email", "password")

    def create(self, validated_data: dict[str, object]) -> User:
        return User.objects.create_user(**validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("email", "name")


class UserProfileExtendedSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    class Meta:
        model = UserProfileSerializer
        fields = "__all__"
    


class OAuthSerializer(serializers.Serializer):
    token = serializers.CharField()
    provider = serializers.ChoiceField(choices=["google", "github", "facebook"])
    