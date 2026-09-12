from django.urls import path

from .views import agent_chat, agent_chat_stream, agent_chat_stream_extension, cancel_stream, csrf_token, health_check, stream_events

app_name = "core"

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("api/csrf/", csrf_token, name="csrf-token"),
    path("api/chat/", agent_chat, name="agent-chat"),
    path("api/chat/stream/", agent_chat_stream, name="agent-chat-stream"),
    path("api/chat/stream/extension/", agent_chat_stream_extension, name="agent-chat-stream-extension"),
    path("api/chat/streams/<uuid:run_id>/events/", stream_events, name="stream-events"),
    path("api/chat/streams/<uuid:run_id>/cancel/", cancel_stream, name="cancel-stream"),
]
