"""Build an ADK agent restricted to one approved read-only function tool."""

import os

from google.adk.agents import Agent

from agent.schemas import ContextResolution, ExecutionPlan, QuestionAnalysis
from agent.tool_registry import (
    ToolBuildContext,
    ToolRegistry,
    default_tool_registry,
)
from agent.validators import validate_execution_plan


class ToolCallingAgentBuildError(ValueError):
    pass


def build_single_tool_calling_agent(
    *,
    plan: ExecutionPlan,
    analysis: QuestionAnalysis,
    context_resolution: ContextResolution,
    tool_context: ToolBuildContext,
    registry: ToolRegistry = default_tool_registry,
) -> Agent:
    """Validate a plan and expose its one approved Tool to Gemini."""

    validate_execution_plan(
        plan,
        analysis=analysis,
        context_resolution=context_resolution,
    )
    tools = registry.tools_for_plan(plan, context=tool_context)
    if len(tools) != 1:
        raise ToolCallingAgentBuildError(
            "single-tool agent requires exactly one executable Tool"
        )

    return Agent(
        name="single_tool_caller",
        model=os.getenv("GEMINI_AGENT_MODEL", "gemini-3.8-flash"),
        description="검증된 계획에 허용된 조회 Tool 하나만 호출한다.",
        instruction="""
사용자 요청을 직접 답하지 말고 제공된 Tool을 정확히 한 번 호출하라.
Tool은 서버가 검증한 조회 전용 기능 하나뿐이다. 사용자 요청에 명시되지 않은
학번, 연도, 학기, 분류 또는 URL을 추측해서 인자로 넣지 마라. 선택 인자가
불명확하면 생략하라. Tool 결과에 없는 사실을 만들거나 Tool 결과를 성공으로
바꾸지 마라. Tool 호출 후에는 결과를 짧게 전달하되 최종 답변 작성은 후속
Response Agent가 담당한다.
""".strip(),
        tools=tools,
        mode="chat",
    )
