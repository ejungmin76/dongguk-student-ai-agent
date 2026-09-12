"""Application service that joins Django ownership state to the ADK runtime."""

from asgiref.sync import async_to_sync

from agent.conversation import DjangoConversationStore
from agent.runtime import StudentAgentRuntime
from agent.schemas import AgentResponse, ValidatedResponse
from apps.conversations.models import ConversationSession, ConversationTurn

from .schemas import ChatResponseSchema


class AgentChatService:
    """Persist safe turns around one ADK call using the same opaque session ID."""

    def __init__(self, *, conversation_store=None, runtime=None) -> None:
        self.conversation_store = conversation_store or DjangoConversationStore()
        self.runtime = runtime or StudentAgentRuntime()

    def chat(self, *, authenticated_subject: str, message: str, session_id: str | None = None) -> ChatResponseSchema:
        prior_history = []
        if session_id is None:
            session = self.conversation_store.create_session(authenticated_subject=authenticated_subject)
        else:
            # Read first to enforce subject ownership and expiry before writing.
            prior_history = self.conversation_store.history(session_id=session_id, authenticated_subject=authenticated_subject)
            session = ConversationSession.objects.get(session_id=session_id)

        self.conversation_store.append_turn(session_id=str(session.session_id), authenticated_subject=authenticated_subject, role=ConversationTurn.Role.USER, message=message)
        runtime_kwargs = {"user_id": authenticated_subject, "session_id": str(session.session_id), "message": message}
        if isinstance(self.runtime, StudentAgentRuntime):
            runtime_kwargs["history"] = prior_history
        result = async_to_sync(self.runtime.run_turn)(**runtime_kwargs)
        if not isinstance(result, (AgentResponse, ValidatedResponse)):
            raise TypeError("agent runtime returned an unsupported response contract")

        response = ChatResponseSchema.from_agent_result(session_id=session.session_id, result=result)
        self.conversation_store.append_turn(
            session_id=str(session.session_id),
            authenticated_subject=authenticated_subject,
            role=ConversationTurn.Role.ASSISTANT,
            message=response.answer,
            response_metadata={
                "status": response.status,
                "source_ids": [source.source_id for source in response.sources],
                "action_ids": [action.action_id for action in response.actions],
            },
        )
        return response
