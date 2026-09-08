from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from time import monotonic
from typing import Callable
from uuid import uuid4

from agent.schemas.error import ErrorDetail
from agent.schemas.result import ToolResult
from agent.schemas.status import ResultStatus
from apps.academic.repositories import AcademicRepository, DjangoAcademicRepository, StudentNotFoundError

from .context import AcademicToolActor
from .record_schemas import AcademicRecordItem, AcademicRecordToolData, AcademicRecordToolInput, CreditSummary
from .tool_support import AcademicAccessDeniedError, AuthenticationRequiredError, resolve_target, result_meta

TOOL_NAME = "get_academic_records"
ZERO = Decimal("0")


def _gpa(records) -> tuple[Decimal, Decimal | None]:
    included = [item for item in records if not item.is_replaced_by_retaking and item.grade_points is not None]
    credits = sum((item.credits_attempted for item in included), ZERO)
    if credits == ZERO:
        return credits, None
    points = sum((item.credits_attempted * item.grade_points for item in included), ZERO)
    return credits, (points / credits).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _summary(key: str, records) -> CreditSummary:
    active = [item for item in records if not item.is_replaced_by_retaking]
    gpa_credits, gpa = _gpa(active)
    return CreditSummary(
        key=key,
        attempted_credits=sum((item.credits_attempted for item in active), ZERO),
        earned_credits=sum((item.credits_earned for item in active), ZERO),
        gpa_credits=gpa_credits,
        gpa=gpa,
    )


class AcademicRecordTool:
    def __init__(self, repository: AcademicRepository):
        self.repository = repository

    def execute(self, request: AcademicRecordToolInput, actor: AcademicToolActor) -> ToolResult[AcademicRecordToolData]:
        started_at, execution_id = monotonic(), str(uuid4())
        try:
            target = resolve_target(actor, request.target_student_number)
            records = self.repository.list_academic_records(target)
        except AuthenticationRequiredError:
            return self._error(execution_id, started_at, "AUTHENTICATION_REQUIRED", "로그인한 학생만 성적을 조회할 수 있습니다.")
        except AcademicAccessDeniedError:
            return self._error(execution_id, started_at, "ACADEMIC_RECORD_ACCESS_DENIED", "다른 학생의 성적은 조회할 수 없습니다.")
        except StudentNotFoundError:
            return self._error(execution_id, started_at, "STUDENT_NOT_FOUND", "학생 정보를 찾을 수 없습니다.")

        selected = tuple(item for item in records if self._matches(item, request))
        active = tuple(item for item in selected if not item.is_replaced_by_retaking)
        gpa_credits, cumulative_gpa = _gpa(active)
        by_term, by_category = defaultdict(list), defaultdict(list)
        for item in selected:
            by_term[f"{item.term.year}-{item.term.semester}"].append(item)
            by_category[item.course.category].append(item)

        data = AcademicRecordToolData(
            student_number=target,
            cumulative_gpa=cumulative_gpa,
            gpa_credits=gpa_credits,
            attempted_credits=sum((item.credits_attempted for item in active), ZERO),
            earned_credits=sum((item.credits_earned for item in active), ZERO),
            term_summaries=tuple(_summary(key, values) for key, values in sorted(by_term.items())),
            category_summaries=tuple(_summary(key, values) for key, values in sorted(by_category.items())),
            records=tuple(self._item(item) for item in selected),
        )
        return ToolResult[AcademicRecordToolData](
            status=ResultStatus.SUCCESS, data=data,
            meta=result_meta(TOOL_NAME, execution_id, started_at),
        )

    @staticmethod
    def _matches(item, request) -> bool:
        return (
            (request.year is None or item.term.year == request.year)
            and (request.semester is None or item.term.semester == request.semester)
            and (request.category is None or item.course.category == request.category)
        )

    @staticmethod
    def _item(item) -> AcademicRecordItem:
        return AcademicRecordItem(
            year=item.term.year, semester=item.term.semester,
            course_code=item.course_code_snapshot, course_name=item.course_name_snapshot,
            category=item.course.category, credits_attempted=item.credits_attempted,
            credits_earned=item.credits_earned, grade=item.grade, grade_points=item.grade_points,
            attempt_number=item.attempt_number, is_replaced_by_retaking=item.is_replaced_by_retaking,
        )

    @staticmethod
    def _error(execution_id, started_at, code, message):
        return ToolResult[AcademicRecordToolData](
            status=ResultStatus.UNAVAILABLE,
            errors=[ErrorDetail(code=code, message=message)],
            meta=result_meta(TOOL_NAME, execution_id, started_at),
        )


def build_get_academic_records_tool(actor: AcademicToolActor, repository: AcademicRepository | None = None) -> Callable[..., dict]:
    service = AcademicRecordTool(repository or DjangoAcademicRepository())

    def get_academic_records(target_student_number: str | None = None, year: int | None = None, semester: str | None = None, category: str | None = None) -> dict:
        """학생의 공식 성적·취득학점·평점을 전체 또는 학기/영역별로 조회한다."""
        request = AcademicRecordToolInput(
            target_student_number=target_student_number, year=year,
            semester=semester, category=category,
        )
        return service.execute(request, actor).model_dump(mode="json")

    return get_academic_records
