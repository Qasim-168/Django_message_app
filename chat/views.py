from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Message
from .serializers import MessageSerializer

User = get_user_model()


class ChatHistoryView(generics.ListAPIView):
    """
    GET /api/chat/history/<user_id>/

    Returns all messages between the authenticated user and the specified
    user, ordered by timestamp (oldest -> newest).
    """

    serializer_class = MessageSerializer

    def get_queryset(self):
        other_user = get_object_or_404(User, pk=self.kwargs["user_id"])
        current_user = self.request.user
        return Message.objects.filter(
            (Q(sender=current_user) & Q(receiver=other_user))
            | (Q(sender=other_user) & Q(receiver=current_user))
        ).select_related("sender", "receiver").order_by("timestamp")
