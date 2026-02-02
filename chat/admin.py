from django.contrib import admin

from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "short_content", "timestamp", "is_read", "is_delivered")
    list_filter = ("is_read", "is_delivered", "timestamp")
    search_fields = ("sender__username", "receiver__username", "content")
    raw_id_fields = ("sender", "receiver")

    @admin.display(description="Content")
    def short_content(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
