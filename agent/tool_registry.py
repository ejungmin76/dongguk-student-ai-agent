"""Server-owned mapping from planner capabilities to ADK function tools."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from asgiref.sync import sync_to_async
from django.db import close_old_connections
from google.adk.tools import FunctionTool

from agent.schemas import Capability, ExecutionPlan
from tools.academic import (
    AcademicToolActor,
    build_get_academic_records_tool,
    build_get_current_schedule_tool,
    build_get_student_profile_tool,
)
from tools.knowledge.search_university_knowledge import (
    build_search_university_knowledge_tool,
)
from tools.ndrims import build_find_ndrims_menu_tool


class ToolRegistryError(ValueError):
    pass


class ToolAuthorizationError(PermissionError):
    pass


@dataclass(frozen=True)
class ToolBuildContext:
    """Trusted dependencies supplied by the server, never by the LLM."""

    actor: AcademicToolActor = field(default_factory=AcademicToolActor)
    academic_repository: Any | None = None
    knowledge_retriever: Any | None = None
    ndrims_retriever: Any | None = None


@dataclass(frozen=True)
class ToolDefinition:
    capability: Capability
    tool_name: str | None
    requires_authenticated_student: bool
    builder: Callable[[ToolBuildContext], Callable[..., Any]] | None


async def _run_sync_tool(sync_tool: Callable[..., dict], **kwargs: Any) -> dict:
    """Run one synchronous service call in an isolated worker DB context."""

    def invoke() -> dict:
        close_old_connections()
        try:
            return sync_tool(**kwargs)
        finally:
            close_old_connections()

    return await sync_to_async(invoke, thread_sensitive=False)()


def _student_profile(context: ToolBuildContext) -> Callable[..., Any]:
    sync_tool = build_get_student_profile_tool(
        context.actor,
        repository=context.academic_repository,
    )

    async def get_student_profile(
        target_student_number: str | None = None,
    ) -> dict:
        """Return the authenticated student's minimum academic profile."""
        return await _run_sync_tool(
            sync_tool,
            target_student_number=target_student_number,
        )

    return get_student_profile


def _academic_records(context: ToolBuildContext) -> Callable[..., Any]:
    sync_tool = build_get_academic_records_tool(
        context.actor,
        repository=context.academic_repository,
    )

    async def get_academic_records(
        target_student_number: str | None = None,
        year: int | None = None,
        semester: str | None = None,
        category: str | None = None,
    ) -> dict:
        """Return grades and earned credits for the authenticated student."""
        return await _run_sync_tool(
            sync_tool,
            target_student_number=target_student_number,
            year=year,
            semester=semester,
            category=category,
        )

    return get_academic_records


def _current_schedule(context: ToolBuildContext) -> Callable[..., Any]:
    sync_tool = build_get_current_schedule_tool(
        context.actor,
        repository=context.academic_repository,
    )

    async def get_current_schedule(
        target_student_number: str | None = None,
    ) -> dict:
        """Return the authenticated student's current courses and timetable."""
        return await _run_sync_tool(
            sync_tool,
            target_student_number=target_student_number,
        )

    return get_current_schedule


def _university_knowledge(context: ToolBuildContext) -> Callable[..., Any]:
    sync_tool = build_search_university_knowledge_tool(context.knowledge_retriever)

    async def search_university_knowledge(
        question: str,
        effective_year: int | None = None,
        effective_on: str | None = None,
        top_k: int = 5,
    ) -> dict:
        """Search official university documents and return citable sources."""
        return await _run_sync_tool(
            sync_tool,
            question=question,
            effective_year=effective_year,
            effective_on=effective_on,
            top_k=top_k,
        )

    return search_university_knowledge


def _ndrims_menu(context: ToolBuildContext) -> Callable[..., Any]:
    sync_tool = build_find_ndrims_menu_tool(context.ndrims_retriever)

    async def find_ndrims_menu(question: str, top_k: int = 5) -> dict:
        """Find verified nDRIMS menus and allowlisted navigation actions."""
        return await _run_sync_tool(
            sync_tool,
            question=question,
            top_k=top_k,
        )

    return find_ndrims_menu


DEFAULT_TOOL_DEFINITIONS = (
    ToolDefinition(
        capability=Capability.STUDENT_PROFILE,
        tool_name="get_student_profile",
        requires_authenticated_student=True,
        builder=_student_profile,
    ),
    ToolDefinition(
        capability=Capability.ACADEMIC_RECORDS,
        tool_name="get_academic_records",
        requires_authenticated_student=True,
        builder=_academic_records,
    ),
    ToolDefinition(
        capability=Capability.CURRENT_SCHEDULE,
        tool_name="get_current_schedule",
        requires_authenticated_student=True,
        builder=_current_schedule,
    ),
    ToolDefinition(
        capability=Capability.UNIVERSITY_KNOWLEDGE,
        tool_name="search_university_knowledge",
        requires_authenticated_student=False,
        builder=_university_knowledge,
    ),
    ToolDefinition(
        capability=Capability.NDRIMS_MENU,
        tool_name="find_ndrims_menu",
        # Menu metadata is public deployment data.  Opening a matched page still
        # requires the student to authenticate with nDRIMS themselves.
        requires_authenticated_student=False,
        builder=_ndrims_menu,
    ),
    ToolDefinition(
        capability=Capability.GENERAL_RESPONSE,
        tool_name=None,
        requires_authenticated_student=False,
        builder=None,
    ),
)


class ToolRegistry:
    """Resolve only capabilities approved by the validated execution plan."""

    def __init__(self, definitions: Iterable[ToolDefinition]) -> None:
        definitions = tuple(definitions)
        by_capability = {item.capability: item for item in definitions}
        if len(by_capability) != len(definitions):
            raise ToolRegistryError("capabilities must be registered exactly once")
        if set(by_capability) != set(Capability):
            missing = set(Capability) - set(by_capability)
            raise ToolRegistryError(f"registry is missing capabilities: {sorted(missing)}")

        names = [item.tool_name for item in definitions if item.tool_name]
        if len(names) != len(set(names)):
            raise ToolRegistryError("tool names must be unique")
        self._definitions = by_capability

    @property
    def definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(self._definitions.values())

    def tool_for_capability(
        self,
        capability: Capability,
        *,
        context: ToolBuildContext,
    ) -> FunctionTool | None:
        definition = self._definitions[capability]
        if definition.builder is None:
            return None
        if (
            definition.requires_authenticated_student
            and context.actor.student_number is None
        ):
            raise ToolAuthorizationError(
                f"{capability} requires an authenticated student"
            )

        function = definition.builder(context)
        tool = FunctionTool(function)
        if tool.name != definition.tool_name:
            raise ToolRegistryError(
                f"registered name {definition.tool_name} does not match {tool.name}"
            )
        return tool

    def tools_for_plan(
        self,
        plan: ExecutionPlan,
        *,
        context: ToolBuildContext,
    ) -> list[FunctionTool]:
        if plan.needs_clarification:
            return []

        tools: list[FunctionTool] = []
        seen: set[Capability] = set()
        for step in plan.steps:
            if step.capability in seen:
                continue
            seen.add(step.capability)
            tool = self.tool_for_capability(step.capability, context=context)
            if tool is not None:
                tools.append(tool)
        return tools


default_tool_registry = ToolRegistry(DEFAULT_TOOL_DEFINITIONS)
