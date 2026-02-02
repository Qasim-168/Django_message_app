from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import Message

User = get_user_model()


class MessageModelTests(TestCase):
    """Tests for the Message model."""

    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="testpass1234")
        self.bob = User.objects.create_user(username="bob", password="testpass1234")

    def test_create_message(self):
        msg = Message.objects.create(
            sender=self.alice, receiver=self.bob, content="Hello Bob"
        )
        self.assertEqual(msg.sender, self.alice)
        self.assertEqual(msg.receiver, self.bob)
        self.assertEqual(msg.content, "Hello Bob")
        self.assertFalse(msg.is_read)
        self.assertFalse(msg.is_delivered)
        self.assertIsNotNone(msg.timestamp)

    def test_ordering_by_timestamp(self):
        m1 = Message.objects.create(sender=self.alice, receiver=self.bob, content="First")
        m2 = Message.objects.create(sender=self.bob, receiver=self.alice, content="Second")
        msgs = list(Message.objects.all())
        self.assertEqual(msgs[0], m1)
        self.assertEqual(msgs[1], m2)

    def test_str_representation(self):
        msg = Message.objects.create(
            sender=self.alice, receiver=self.bob, content="Hi"
        )
        self.assertIn("alice", str(msg))
        self.assertIn("bob", str(msg))


class ChatHistoryAPITests(TestCase):
    """Tests for GET /api/chat/history/<user_id>/"""

    def setUp(self):
        self.client = APIClient()
        self.alice = User.objects.create_user(username="alice", password="testpass1234")
        self.bob = User.objects.create_user(username="bob", password="testpass1234")
        self.charlie = User.objects.create_user(username="charlie", password="testpass1234")

        # Messages between alice and bob
        Message.objects.create(sender=self.alice, receiver=self.bob, content="Hi Bob")
        Message.objects.create(sender=self.bob, receiver=self.alice, content="Hi Alice")
        Message.objects.create(sender=self.alice, receiver=self.bob, content="How are you?")

        # Message between alice and charlie (should NOT appear in alice-bob history)
        Message.objects.create(sender=self.alice, receiver=self.charlie, content="Hi Charlie")

    def test_history_returns_correct_messages(self):
        self.client.force_authenticate(user=self.alice)
        resp = self.client.get(f"/api/chat/history/{self.bob.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 3)

    def test_history_excludes_other_chats(self):
        self.client.force_authenticate(user=self.bob)
        resp = self.client.get(f"/api/chat/history/{self.alice.pk}/")
        # Bob should see only the 3 messages with Alice, not Charlie's
        self.assertEqual(len(resp.data), 3)

    def test_history_ordered_oldest_first(self):
        self.client.force_authenticate(user=self.alice)
        resp = self.client.get(f"/api/chat/history/{self.bob.pk}/")
        self.assertEqual(resp.data[0]["content"], "Hi Bob")
        self.assertEqual(resp.data[-1]["content"], "How are you?")

    def test_history_unauthenticated(self):
        resp = self.client.get(f"/api/chat/history/{self.bob.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_history_nonexistent_user(self):
        self.client.force_authenticate(user=self.alice)
        resp = self.client.get("/api/chat/history/99999/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_history_response_fields(self):
        self.client.force_authenticate(user=self.alice)
        resp = self.client.get(f"/api/chat/history/{self.bob.pk}/")
        msg = resp.data[0]
        self.assertIn("id", msg)
        self.assertIn("sender", msg)
        self.assertIn("receiver", msg)
        self.assertIn("content", msg)
        self.assertIn("timestamp", msg)
        self.assertIn("sender_username", msg)
        self.assertIn("receiver_username", msg)
        self.assertIn("is_read", msg)
        self.assertIn("is_delivered", msg)

    def test_history_symmetric(self):
        """Both participants should see the same messages."""
        self.client.force_authenticate(user=self.alice)
        resp_a = self.client.get(f"/api/chat/history/{self.bob.pk}/")

        self.client.force_authenticate(user=self.bob)
        resp_b = self.client.get(f"/api/chat/history/{self.alice.pk}/")

        self.assertEqual(len(resp_a.data), len(resp_b.data))
        for a, b in zip(resp_a.data, resp_b.data):
            self.assertEqual(a["id"], b["id"])


class WebSocketConsumerTests(TestCase):
    """
    Synchronous-only sanity checks for consumer logic.
    Full async WebSocket tests require channels[testing] with an async
    test runner and a running channel layer (see integration tests / Docker).
    """

    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="testpass1234")
        self.bob = User.objects.create_user(username="bob", password="testpass1234")

    def test_message_persisted_on_save(self):
        """Verify the ORM path the consumer uses to persist messages."""
        msg = Message.objects.create(
            sender=self.alice, receiver=self.bob, content="persisted"
        )
        self.assertTrue(Message.objects.filter(pk=msg.pk).exists())

    def test_mark_delivered(self):
        msg = Message.objects.create(
            sender=self.alice, receiver=self.bob, content="deliver me"
        )
        Message.objects.filter(pk=msg.pk, receiver=self.bob, is_delivered=False).update(
            is_delivered=True
        )
        msg.refresh_from_db()
        self.assertTrue(msg.is_delivered)

    def test_mark_read(self):
        msg = Message.objects.create(
            sender=self.alice, receiver=self.bob, content="read me"
        )
        Message.objects.filter(pk=msg.pk, receiver=self.bob, is_read=False).update(
            is_read=True, is_delivered=True
        )
        msg.refresh_from_db()
        self.assertTrue(msg.is_read)
        self.assertTrue(msg.is_delivered)

    def test_mark_delivered_wrong_receiver_ignored(self):
        """Only the actual receiver can mark a message as delivered."""
        msg = Message.objects.create(
            sender=self.alice, receiver=self.bob, content="nope"
        )
        # Attempt to mark delivered as alice (the sender) – should not change
        updated = Message.objects.filter(
            pk=msg.pk, receiver=self.alice, is_delivered=False
        ).update(is_delivered=True)
        self.assertEqual(updated, 0)
        msg.refresh_from_db()
        self.assertFalse(msg.is_delivered)
