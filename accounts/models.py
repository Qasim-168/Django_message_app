from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """Extends the built-in User with online/offline status tracking."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({'online' if self.is_online else 'offline'})"
