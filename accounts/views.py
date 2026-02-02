from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from .serializers import RegisterSerializer, UserSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """Register a new user (no authentication required)."""

    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class UserListView(generics.ListAPIView):
    """List all users (authenticated only). Useful for finding chat partners."""

    serializer_class = UserSerializer
    queryset = User.objects.select_related("profile").all()


class UserDetailView(generics.RetrieveAPIView):
    """Retrieve a single user's public info and online status."""

    serializer_class = UserSerializer
    queryset = User.objects.select_related("profile").all()
