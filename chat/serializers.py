from rest_framework import serializers

from .models import Message


class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source="sender.username", read_only=True)
    receiver_username = serializers.CharField(source="receiver.username", read_only=True)

    class Meta:
        model = Message
        fields = (
            "id",
            "sender",
            "sender_username",
            "receiver",
            "receiver_username",
            "content",
            "timestamp",
            "is_read",
            "is_delivered",
        )
        read_only_fields = ("id", "sender", "timestamp", "is_read", "is_delivered")
