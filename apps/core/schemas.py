"""Pydantic contracts at the public Django chat API boundary."""

from uuid import UUID

from pydantic import ConfigDict, Field

from agent.schemas import ActionReference, AgentResponse, ResultStatus, SourceReference, ValidatedResponse
from agent.schemas.base import ContractModel


class ChatRequestSchema(ContractModel):
    """The browser may choose an existing session, but never a user identity."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=2_000)
    session_id: UUID | None = None


class ChatResponseSchema(ContractModel):
    """Stable JSON contract for both initial and fully grounded agent responses."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    status: ResultStatus
    answer: str = Field(min_length=1, max_length=500)
    sources: list[SourceReference] = Field(default_factory=list)
    actions: list[ActionReference] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list, max_length=3)
    follow_up_question: str | None = Field(default=None, max_length=200)

    @classmethod
    def from_agent_result(
        cls, *, session_id: UUID, result: AgentResponse | ValidatedResponse
    ) -> "ChatResponseSchema":
        if isinstance(result, ValidatedResponse):
            return cls(session_id=session_id, status=result.status, answer=result.answer, sources=result.sources, actions=result.actions, limitations=result.limitations, follow_up_question=result.follow_up_question)
        return cls(session_id=session_id, status=result.status, answer=result.answer, follow_up_question=result.follow_up_question)
