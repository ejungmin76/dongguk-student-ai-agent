from time import monotonic

from agent.schemas.meta import ResultMeta


class AuthenticationRequiredError(PermissionError):
    pass


class AcademicAccessDeniedError(PermissionError):
    pass


def resolve_target(actor, target_student_number: str | None) -> str:
    if actor.student_number is None:
        raise AuthenticationRequiredError
    target = target_student_number or actor.student_number
    if target != actor.student_number and not actor.can_read_other_profiles:
        raise AcademicAccessDeniedError
    return target


def result_meta(tool_name: str, execution_id: str, started_at: float) -> ResultMeta:
    return ResultMeta(
        tool_name=tool_name,
        execution_id=execution_id,
        duration_ms=max(0, round((monotonic() - started_at) * 1000)),
    )
