from django.urls import path

from .views import agent_chat, agent_chat_stream, cancel_stream, health_check, stream_events

app_name = "core"

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("api/chat/", agent_chat, name="agent-chat"),
    path("api/chat/stream/", agent_chat_stream, name="agent-chat-stream"),
    path("api/chat/streams/<uuid:run_id>/events/", stream_events, name="stream-events"),
    path("api/chat/streams/<uuid:run_id>/cancel/", cancel_stream, name="cancel-stream"),
]
