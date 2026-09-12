"""Deterministic dependency-aware execution of server-approved ADK tools."""

import asyncio
import inspect
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from agent.schemas import (
    Capability,
    ContextResolution,
    ErrorDetail,
    ExecutionPlan,
    ExecutionStep,
    PlanExecutionResult,
    QuestionAnalysis,
    ResultStatus,
    StepExecutionState,
    ToolStepExecution,
)
from agent.tool_registry import (
    ToolBuildContext,
    ToolRegistry,
    default_tool_registry,
)
from agent.validators import validate_execution_plan


class MultiToolExecutionError(ValueError):
    pass


DependencyResults = Mapping[str, ToolStepExecution]
StepArgumentResolver = Callable[
    [ExecutionStep, str, DependencyResults],
    Mapping[str, Any] | Awaitable[Mapping[str, Any]],
]


def build_execution_waves(plan: ExecutionPlan) -> list[list[str]]:
    """Group topologically ordered steps that can start at the same time."""

    wave_by_step: dict[str, int] = {}
    waves: list[list[str]] = []
    for step in plan.steps:
        wave_number = (
            max(wave_by_step[dependency] for dependency in step.depends_on) + 1
            if step.depends_on
            else 0
        )
        wave_by_step[step.step_id] = wave_number
        while len(waves) <= wave_number:
            waves.append([])
        waves[wave_number].append(step.step_id)
    return waves


def default_step_arguments(
    step: ExecutionStep,
    question: str,
    dependency_results: DependencyResults,
) -> Mapping[str, Any]:
    """Supply only universally valid arguments; never infer optional filters."""

    del dependency_results
    if step.capability in {
        Capability.UNIVERSITY_KNOWLEDGE,
        Capability.NDRIMS_MENU,
    }:
        return {"question": question}
    return {}


class MultiToolExecutor:
    """Execute independent waves concurrently and dependency waves in order."""

    def __init__(
        self,
        *,
        registry: ToolRegistry = default_tool_registry,
        step_timeout_seconds: float = 15.0,
        argument_resolver: StepArgumentResolver = default_step_arguments,
    ) -> None:
        if step_timeout_seconds <= 0:
            raise ValueError("step_timeout_seconds must be positive")
        self.registry = registry
        self.step_timeout_seconds = step_timeout_seconds
        self.argument_resolver = argument_resolver

    async def execute(
        self,
        *,
        plan: ExecutionPlan,
        analysis: QuestionAnalysis,
        context_resolution: ContextResolution,
        tool_context: ToolBuildContext,
        question: str,
    ) -> PlanExecutionResult:
        validate_execution_plan(
            plan,
            analysis=analysis,
            context_resolution=context_resolution,
        )
        if plan.needs_clarification:
            raise MultiToolExecutionError("clarification plans are not executable")

        question = question.strip()
        if not question:
            raise MultiToolExecutionError("question must not be empty")

        steps_by_id = {step.step_id: step for step in plan.steps}
        waves = build_execution_waves(plan)
        results: dict[str, ToolStepExecution] = {}
        started_at = time.perf_counter()

        for wave in waves:
            wave_results = await asyncio.gather(
                *(
                    self._run_or_block(
                        step=steps_by_id[step_id],
                        question=question,
                        completed=results,
                        tool_context=tool_context,
                    )
                    for step_id in wave
                )
            )
            results.update({result.step_id: result for result in wave_results})

        ordered_results = [results[step.step_id] for step in plan.steps]
        return PlanExecutionResult(
            status=self._aggregate_status(ordered_results),
            steps=ordered_results,
            execution_waves=waves,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
        )

    async def _run_or_block(
        self,
        *,
        step: ExecutionStep,
        question: str,
        completed: Mapping[str, ToolStepExecution],
        tool_context: ToolBuildContext,
    ) -> ToolStepExecution:
        dependency_results = {
            dependency: completed[dependency] for dependency in step.depends_on
        }
        failed_dependencies = [
            step_id
            for step_id, result in dependency_results.items()
            if not result.is_usable
        ]
        if failed_dependencies:
            return ToolStepExecution(
                step_id=step.step_id,
                capability=step.capability,
                state=StepExecutionState.BLOCKED,
                error=ErrorDetail(
                    code="DEPENDENCY_UNAVAILABLE",
                    message=(
                        "선행 단계가 완료되지 않아 실행하지 않았습니다: "
                        + ", ".join(failed_dependencies)
                    ),
                ),
                duration_ms=0,
            )

        started_at = time.perf_counter()
        tool_name: str | None = None
        try:
            tool = self.registry.tool_for_capability(
                step.capability,
                context=tool_context,
            )
            if tool is None:
                raise MultiToolExecutionError(
                    f"{step.capability} does not map to an executable Tool"
                )
            tool_name = tool.name
            arguments = self.argument_resolver(
                step,
                question,
                dependency_results,
            )
            if inspect.isawaitable(arguments):
                arguments = await arguments
            if not isinstance(arguments, Mapping):
                raise TypeError("argument resolver must return a mapping")

            output = await asyncio.wait_for(
                tool.func(**dict(arguments)),
                timeout=self.step_timeout_seconds,
            )
            if not isinstance(output, dict):
                raise TypeError("Tool output must be a dictionary")
            state = self._state_from_tool_output(output)
            return ToolStepExecution(
                step_id=step.step_id,
                capability=step.capability,
                tool_name=tool_name,
                state=state,
                output=output,
                duration_ms=int((time.perf_counter() - started_at) * 1000),
            )
        except TimeoutError:
            return self._failure(
                step=step,
                tool_name=tool_name,
                state=StepExecutionState.TIMED_OUT,
                code="TOOL_TIMEOUT",
                message="도구 실행 제한 시간을 초과했습니다.",
                started_at=started_at,
                retryable=True,
            )
        except Exception:
            return self._failure(
                step=step,
                tool_name=tool_name,
                state=StepExecutionState.ERROR,
                code="TOOL_EXECUTION_ERROR",
                message="도구 실행 중 처리되지 않은 오류가 발생했습니다.",
                started_at=started_at,
            )

    @staticmethod
    def _state_from_tool_output(output: Mapping[str, Any]) -> StepExecutionState:
        try:
            status = ResultStatus(output["status"])
        except (KeyError, ValueError, TypeError) as error:
            raise ValueError("Tool output has an invalid status") from error
        return {
            ResultStatus.SUCCESS: StepExecutionState.SUCCESS,
            ResultStatus.PARTIAL: StepExecutionState.PARTIAL,
            ResultStatus.UNAVAILABLE: StepExecutionState.UNAVAILABLE,
            ResultStatus.CLARIFICATION: StepExecutionState.CLARIFICATION,
        }[status]

    @staticmethod
    def _failure(
        *,
        step: ExecutionStep,
        tool_name: str | None,
        state: StepExecutionState,
        code: str,
        message: str,
        started_at: float,
        retryable: bool = False,
    ) -> ToolStepExecution:
        return ToolStepExecution(
            step_id=step.step_id,
            capability=step.capability,
            tool_name=tool_name,
            state=state,
            error=ErrorDetail(
                code=code,
                message=message,
                retryable=retryable,
            ),
            duration_ms=int((time.perf_counter() - started_at) * 1000),
        )

    @staticmethod
    def _aggregate_status(results: list[ToolStepExecution]) -> ResultStatus:
        usable_count = sum(result.is_usable for result in results)
        if usable_count == len(results) and all(
            result.state == StepExecutionState.SUCCESS for result in results
        ):
            return ResultStatus.SUCCESS
        if usable_count:
            return ResultStatus.PARTIAL
        return ResultStatus.UNAVAILABLE

