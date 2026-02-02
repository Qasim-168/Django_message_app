"""Root URL configuration."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/chat/", include("chat.urls")),
    # Minimal chat UI (served at root)
    path("", TemplateView.as_view(template_name="chat/index.html"), name="chat-home"),
]
