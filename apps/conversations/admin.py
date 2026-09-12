from django.contrib import admin

from .models import ConversationSession, ConversationTurn


class ConversationTurnInline(admin.TabularInline):
    model = ConversationTurn
    extra = 0
    can_delete = False
    readonly_fields = ("sequence", "role", "message", "response_metadata", "created_at")


@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    list_display = ("session_id", "status", "expires_at", "last_activity_at", "version")
    list_filter = ("status",)
    search_fields = ("session_id", "subject_key")
    readonly_fields = ("session_id", "subject_key", "created_at", "updated_at")
    inlines = (ConversationTurnInline,)
