from decimal import Decimal
from time import monotonic
from typing import Callable
from uuid import uuid4

from agent.schemas.error import ErrorDetail
from agent.schemas.result import ToolResult
from agent.schemas.status import ResultStatus
from apps.academic.repositories import AcademicRepository, DjangoAcademicRepository, StudentNotFoundError

from .context import AcademicToolActor
from .schedule_schemas import CurrentCourseItem, CurrentScheduleToolData, CurrentScheduleToolInput, MeetingItem, ScheduleConflict
from .tool_support import AcademicAccessDeniedError, AuthenticationRequiredError, resolve_target, result_meta

TOOL_NAME = "get_current_schedule"


class CurrentScheduleTool:
    def __init__(self, repository: AcademicRepository):
        self.repository = repository

    def execute(self, request: CurrentScheduleToolInput, actor: AcademicToolActor) -> ToolResult[CurrentScheduleToolData]:
        started_at, execution_id = monotonic(), str(uuid4())
        try:
            target = resolve_target(actor, request.target_student_number)
            profile = self.repository.get_student_profile(target)
            enrollments = self.repository.list_current_enrollments(target)
        except AuthenticationRequiredError:
            return self._error(execution_id, started_at, "AUTHENTICATION_REQUIRED", "로그인한 학생만 시간표를 조회할 수 있습니다.")
        except AcademicAccessDeniedError:
            return self._error(execution_id, started_at, "SCHEDULE_ACCESS_DENIED", "다른 학생의 시간표는 조회할 수 없습니다.")
        except StudentNotFoundError:
            return self._error(execution_id, started_at, "STUDENT_NOT_FOUND", "학생 정보를 찾을 수 없습니다.")

        courses = tuple(
            CurrentCourseItem(
                course_code=item.course.code, course_name=item.course.name,
                category=item.course.category, credits=item.course.credits,
                section_number=item.section_number, professor_name=item.professor_name,
                meetings=tuple(MeetingItem(**meeting.model_dump()) for meeting in item.meetings),
            )
            for item in enrollments
        )
        conflicts = self._conflicts(courses)
        reference_term = profile.reference_term
        data = CurrentScheduleToolData(
            student_number=target,
            year=reference_term.year if reference_term else None,
            semester=reference_term.semester if reference_term else None,
            total_credits=sum((item.credits for item in courses), Decimal("0")),
            courses=courses,
            conflicts=conflicts,
        )
        if conflicts:
            return ToolResult[CurrentScheduleToolData](
                status=ResultStatus.PARTIAL, data=data,
                errors=[ErrorDetail(code="SCHEDULE_CONFLICT", message="서로 겹치는 수업 시간이 있습니다.")],
                meta=result_meta(TOOL_NAME, execution_id, started_at),
            )
        return ToolResult[CurrentScheduleToolData](
            status=ResultStatus.SUCCESS, data=data,
            meta=result_meta(TOOL_NAME, execution_id, started_at),
        )

    @staticmethod
    def _conflicts(courses) -> tuple[ScheduleConflict, ...]:
        conflicts = []
        for first_index, first in enumerate(courses):
            for second in courses[first_index + 1:]:
                for first_meeting in first.meetings:
                    for second_meeting in second.meetings:
                        if first_meeting.day_of_week != second_meeting.day_of_week:
                            continue
                        start = max(first_meeting.start_time, second_meeting.start_time)
                        end = min(first_meeting.end_time, second_meeting.end_time)
                        if start < end:
                            conflicts.append(ScheduleConflict(
                                day_of_week=first_meeting.day_of_week,
                                first_course_code=first.course_code,
                                second_course_code=second.course_code,
                                overlap_start=start, overlap_end=end,
                            ))
        return tuple(conflicts)

    @staticmethod
    def _error(execution_id, started_at, code, message):
        return ToolResult[CurrentScheduleToolData](
            status=ResultStatus.UNAVAILABLE,
            errors=[ErrorDetail(code=code, message=message)],
            meta=result_meta(TOOL_NAME, execution_id, started_at),
        )


def build_get_current_schedule_tool(actor: AcademicToolActor, repository: AcademicRepository | None = None) -> Callable[..., dict]:
    service = CurrentScheduleTool(repository or DjangoAcademicRepository())

    def get_current_schedule(target_student_number: str | None = None) -> dict:
        """학생 기준 학기의 현재 수강 과목, 학점, 수업시간과 충돌을 조회한다."""
        request = CurrentScheduleToolInput(target_student_number=target_student_number)
        return service.execute(request, actor).model_dump(mode="json")

    return get_current_schedule
