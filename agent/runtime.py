"""Programmatic runtime for the public evidence-first Agent."""

from .orchestrator import PublicAgentOrchestrator
from .schemas import ValidatedResponse


APP_NAME = "dongguk_student_ai"


class StudentAgentRuntime:
    """Compatibility name for the chat service's public Agent runtime."""

    def __init__(self, orchestrator: PublicAgentOrchestrator | None = None) -> None:
        self.orchestrator = orchestrator or PublicAgentOrchestrator()

    async def run_turn(
        self,
        *,
        user_id: str,
        session_id: str,
        message: str,
    ) -> ValidatedResponse:
        # Ownership/history is managed by DjangoConversationStore.  These opaque
        # identifiers are accepted for the stable runtime interface only.
        del user_id, session_id
        return await self.orchestrator.run(question=message)
