import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from .models import Message

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for one-to-one real-time chat.

    URL:  ws://<host>/ws/chat/<user_id>/?token=<jwt_access_token>

    Supported incoming message types:
      - chat_message : send a text message
      - typing       : broadcast typing indicator
      - read_receipt : mark messages as read
    """

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self):
        self.other_user_id = int(self.scope["url_route"]["kwargs"]["user_id"])
        self.user = self.scope.get("user", AnonymousUser())

        # 1. Reject unauthenticated users
        if isinstance(self.user, AnonymousUser) or not self.user.is_authenticated:
            await self.close()
            return

        # 2. Ensure the target user exists
        self.other_user = await self._get_user(self.other_user_id)
        if self.other_user is None:
            await self.close()
            return

        # 3. Prevent chatting with yourself
        if self.user.id == self.other_user.id:
            await self.close()
            return

        # 4. Deterministic room name so both participants share the same group
        ids = sorted([self.user.id, self.other_user.id])
        self.room_group_name = f"chat_{ids[0]}_{ids[1]}"

        await self.channel_layer.group_add(
            self.room_group_name, self.channel_name
        )
        await self.accept()

        # Mark user online and notify the partner
        await self._set_online(True)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_status",
                "user_id": self.user.id,
                "username": self.user.username,
                "status": "online",
            },
        )

    async def disconnect(self, close_code):
        if not hasattr(self, "room_group_name"):
            return

        await self._set_online(False)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_status",
                "user_id": self.user.id,
                "username": self.user.username,
                "status": "offline",
            },
        )
        await self.channel_layer.group_discard(
            self.room_group_name, self.channel_name
        )

    # ------------------------------------------------------------------
    # Incoming message dispatcher
    # ------------------------------------------------------------------

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON"}))
            return

        msg_type = data.get("type", "chat_message")

        if msg_type == "chat_message":
            await self._handle_chat_message(data)
        elif msg_type == "typing":
            await self._handle_typing(data)
        elif msg_type == "read_receipt":
            await self._handle_read_receipt(data)

    # ------------------------------------------------------------------
    # Handlers for each incoming message type
    # ------------------------------------------------------------------

    async def _handle_chat_message(self, data):
        content = data.get("message", "").strip()
        if not content:
            return

        message = await self._save_message(content)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message_id": message.id,
                "message": content,
                "sender_id": self.user.id,
                "sender_username": self.user.username,
                "timestamp": message.timestamp.isoformat(),
                "is_delivered": False,
                "is_read": False,
            },
        )

    async def _handle_typing(self, data):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "typing_indicator",
                "user_id": self.user.id,
                "username": self.user.username,
                "is_typing": bool(data.get("is_typing", False)),
            },
        )

    async def _handle_read_receipt(self, data):
        message_ids = data.get("message_ids", [])
        if not message_ids:
            return
        await self._mark_messages_read(message_ids)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "read_receipt",
                "message_ids": message_ids,
                "reader_id": self.user.id,
            },
        )

    # ------------------------------------------------------------------
    # Group-event handlers (called by channel layer)
    # ------------------------------------------------------------------

    async def chat_message(self, event):
        # When the receiver gets the message, mark it as delivered
        if event["sender_id"] != self.user.id:
            await self._mark_message_delivered(event["message_id"])
            event["is_delivered"] = True

        await self.send(
            text_data=json.dumps(
                {
                    "type": "chat_message",
                    "message_id": event["message_id"],
                    "message": event["message"],
                    "sender_id": event["sender_id"],
                    "sender_username": event["sender_username"],
                    "timestamp": event["timestamp"],
                    "is_delivered": event.get("is_delivered", False),
                    "is_read": event.get("is_read", False),
                }
            )
        )

    async def typing_indicator(self, event):
        # Only forward to the *other* participant
        if event["user_id"] != self.user.id:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "typing",
                        "user_id": event["user_id"],
                        "username": event["username"],
                        "is_typing": event["is_typing"],
                    }
                )
            )

    async def user_status(self, event):
        if event["user_id"] != self.user.id:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "user_status",
                        "user_id": event["user_id"],
                        "username": event["username"],
                        "status": event["status"],
                    }
                )
            )

    async def read_receipt(self, event):
        if event["reader_id"] != self.user.id:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "read_receipt",
                        "message_ids": event["message_ids"],
                        "reader_id": event["reader_id"],
                    }
                )
            )

    # ------------------------------------------------------------------
    # Database helpers (all wrapped for async)
    # ------------------------------------------------------------------

    @database_sync_to_async
    def _get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def _save_message(self, content):
        return Message.objects.create(
            sender=self.user,
            receiver=self.other_user,
            content=content,
        )

    @database_sync_to_async
    def _mark_message_delivered(self, message_id):
        Message.objects.filter(
            pk=message_id, receiver=self.user, is_delivered=False
        ).update(is_delivered=True)

    @database_sync_to_async
    def _mark_messages_read(self, message_ids):
        Message.objects.filter(
            pk__in=message_ids, receiver=self.user, is_read=False
        ).update(is_read=True, is_delivered=True)

    @database_sync_to_async
    def _set_online(self, online):
        from accounts.models import UserProfile

        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.is_online = online
        if not online:
            profile.last_seen = timezone.now()
        profile.save(update_fields=["is_online", "last_seen"])
