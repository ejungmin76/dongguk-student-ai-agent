from time import monotonic
from typing import Callable
from uuid import uuid4

from agent.schemas.error import ErrorDetail
from agent.schemas.meta import ResultMeta
from agent.schemas.result import ToolResult
from agent.schemas.status import ResultStatus
from apps.academic.repositories import (
    AcademicRepository,
    DjangoAcademicRepository,
    StudentNotFoundError,
)

from .context import AcademicToolActor
from .profile_schemas import StudentProfileToolData, StudentProfileToolInput

TOOL_NAME = "get_student_profile"


class StudentProfileTool:
    def __init__(self, repository: AcademicRepository):
        self.repository = repository

    def execute(
        self,
        request: StudentProfileToolInput,
        actor: AcademicToolActor,
    ) -> ToolResult[StudentProfileToolData]:
        started_at = monotonic()
        execution_id = str(uuid4())

        if actor.student_number is None:
            return self._unavailable(
                execution_id, started_at, "AUTHENTICATION_REQUIRED",
                "로그인한 학생만 프로필을 조회할 수 있습니다.",
            )

        target = request.target_student_number or actor.student_number
        if target != actor.student_number and not actor.can_read_other_profiles:
            return self._unavailable(
                execution_id, started_at, "PROFILE_ACCESS_DENIED",
                "다른 학생의 프로필은 조회할 수 없습니다.",
            )

        try:
            profile = self.repository.get_student_profile(target)
        except StudentNotFoundError:
            return self._unavailable(
                execution_id, started_at, "STUDENT_NOT_FOUND",
                "학생 정보를 찾을 수 없습니다.",
            )

        return ToolResult[StudentProfileToolData](
            status=ResultStatus.SUCCESS,
            data=StudentProfileToolData(
                student_number=profile.student_number,
                display_name=profile.display_name,
                admission_year=profile.admission_year,
                current_semester=profile.current_semester,
                status=profile.status,
                program_track=profile.program_track,
                primary_major_name=profile.primary_major.name,
                secondary_major_name=(
                    profile.secondary_major.name if profile.secondary_major else None
                ),
            ),
            meta=self._meta(execution_id, started_at),
        )

    @staticmethod
    def _meta(execution_id: str, started_at: float) -> ResultMeta:
        return ResultMeta(
            tool_name=TOOL_NAME,
            execution_id=execution_id,
            duration_ms=max(0, round((monotonic() - started_at) * 1000)),
        )

    def _unavailable(
        self, execution_id: str, started_at: float, code: str, message: str
    ) -> ToolResult[StudentProfileToolData]:
        return ToolResult[StudentProfileToolData](
            status=ResultStatus.UNAVAILABLE,
            errors=[ErrorDetail(code=code, message=message)],
            meta=self._meta(execution_id, started_at),
        )


def build_get_student_profile_tool(
    actor: AcademicToolActor,
    repository: AcademicRepository | None = None,
) -> Callable[[str | None], dict]:
    """인증 주체가 고정된 ADK 호환 Python Tool 함수를 생성한다."""
    service = StudentProfileTool(repository or DjangoAcademicRepository())

    def get_student_profile(target_student_number: str | None = None) -> dict:
        """로그인한 학생의 최소 학적 프로필을 조회한다.

        Args:
            target_student_number: 생략하면 로그인한 본인을 조회한다.
                다른 학번은 서버가 부여한 권한이 있을 때만 조회할 수 있다.

        Returns:
            상태와 최소 학생 프로필 또는 안전한 오류가 담긴 JSON 객체.
        """
        request = StudentProfileToolInput(
            target_student_number=target_student_number
        )
        return service.execute(request, actor).model_dump(mode="json")

    return get_student_profile
