from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import UserProfile

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )


class UserSerializer(serializers.ModelSerializer):
    is_online = serializers.BooleanField(source="profile.is_online", read_only=True)
    last_seen = serializers.DateTimeField(source="profile.last_seen", read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "is_online", "last_seen")
