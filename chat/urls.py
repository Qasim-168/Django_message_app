from django.urls import path

from . import views

urlpatterns = [
    path(
        "history/<int:user_id>/",
        views.ChatHistoryView.as_view(),
        name="chat-history",
    ),
]
