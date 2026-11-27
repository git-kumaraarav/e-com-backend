from rest_framework import serializers

from .models import InstagramPost


class InstagramPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstagramPost
        fields = "__all__"
