from django.urls import path

from .views import agent_chat, health_check

app_name = "core"

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("api/chat/", agent_chat, name="agent-chat"),
]
