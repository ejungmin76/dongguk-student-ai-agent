from pydantic import Field

from agent.schemas.base import ContractModel


class AcademicToolActor(ContractModel):
    """Django 인증 계층이 생성하고 LLM은 변경할 수 없는 실행 주체."""

    student_number: str | None = Field(default=None, min_length=1, max_length=20)
    can_read_other_profiles: bool = False
