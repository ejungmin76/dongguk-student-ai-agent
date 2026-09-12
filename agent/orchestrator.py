"""Public, evidence-first assembly of the individual Agent components."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar
from uuid import uuid4

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel

from agent.context_builder import ContextBuilder
from agent.executors import MultiToolExecutor
from agent.fallback import FallbackPolicy
from agent.planners.context_resolver import resolve_question_context
from agent.planners.execution_planner import (
    build_execution_planner_input,
    execution_planner_agent,
)
from agent.planners.question_analyzer import question_analyzer_agent
from agent.public_mode import PUBLIC_CAPABILITIES, assert_public_plan
from agent.responders import ResponseAgentRuntime
from agent.schemas import (
    ActionReference,
    ActionType,
    Capability,
    ExecutionPlan,
    QuestionAnalysis,
    ResponseContext,
    ResponseDraft,
    ResultStatus,
    ValidatedResponse,
)
from agent.tool_registry import ToolBuildContext


Model = TypeVar("Model", bound=BaseModel)
Analyzer = Callable[[str], Awaitable[QuestionAnalysis]]
Planner = Callable[[str, QuestionAnalysis], Awaitable[ExecutionPlan]]
Responder = Callable[[str, ResponseContext], Awaitable[ResponseDraft]]

NDRIMS_MAIN_URL = "https://ndrims.dongguk.edu/main/main.clx"


class StructuredAgentRunner:
    """Small reusable ADK runner for one structured, no-tool Agent turn."""

    def __init__(self, *, app_name: str, agent: Agent, schema: type[Model]) -> None:
        self.schema = schema
        self.session_service = InMemorySessionService()
        self.runner = Runner(
            app_name=app_name,
            agent=agent,
            session_service=self.session_service,
            auto_create_session=True,
        )

    async def run(self, message: str) -> Model:
        session_id = str(uuid4())
        result: Model | None = None
        async for event in self.runner.run_async(
            user_id="public-browser",
            session_id=session_id,
            new_message=types.Content(role="user", parts=[types.Part(text=message)]),
        ):
            if not event.is_final_response():
                continue
            if isinstance(event.output, dict):
                result = self.schema.model_validate(event.output)
                continue
            text = "".join(
                part.text
                for part in (event.content.parts if event.content else [])
                if part.text
            )
            if text:
                result = self.schema.model_validate_json(text)
        if result is None:
            raise RuntimeError(f"{self.runner.agent.name} returned no structured result")
        return result


class PublicAgentOrchestrator:
    """Run only public capabilities from question analysis through validation.

    Personal capability requests deliberately exit before planning/execution.  This
    makes the deployment boundary enforceable even if a model misclassifies a
    sentence or later prompts are changed.
    """

    def __init__(
        self,
        *,
        analyzer: Analyzer | None = None,
        planner: Planner | None = None,
        responder: Responder | None = None,
        executor: MultiToolExecutor | None = None,
        context_builder: ContextBuilder | None = None,
        fallback_policy: FallbackPolicy | None = None,
        tool_context: ToolBuildContext | None = None,
    ) -> None:
        analyzer_runtime = StructuredAgentRunner(
            app_name="dongguk_public_question_analysis",
            agent=question_analyzer_agent,
            schema=QuestionAnalysis,
        )
        planner_runtime = StructuredAgentRunner(
            app_name="dongguk_public_execution_planning",
            agent=execution_planner_agent,
            schema=ExecutionPlan,
        )
        response_runtime = ResponseAgentRuntime()

        self.analyzer = analyzer or analyzer_runtime.run
        self.planner = planner or (
            lambda question, analysis: planner_runtime.run(
                build_execution_planner_input(
                    question=question,
                    analysis=analysis,
                    context_resolution=resolve_question_context(analysis),
                )
            )
        )
        self.responder = responder or (
            lambda question, context: response_runtime.generate(
                question=question,
                context=context,
            )
        )
        self.executor = executor or MultiToolExecutor()
        self.context_builder = context_builder or ContextBuilder()
        self.fallback_policy = fallback_policy or FallbackPolicy()
        self.tool_context = tool_context or ToolBuildContext()

    async def run(self, *, question: str) -> ValidatedResponse:
        question = question.strip()
        if not question:
            return self._unavailable()

        try:
            analysis = await self.analyzer(question)
            private_capabilities = set(analysis.capabilities) - PUBLIC_CAPABILITIES
            if private_capabilities:
                return self._personal_data_boundary()
            if analysis.needs_clarification:
                return ValidatedResponse(
                    status=ResultStatus.CLARIFICATION,
                    answer="정확히 안내하려면 한 가지 정보를 더 확인해야 해요.",
                    follow_up_question=analysis.clarification_question,
                )

            executable = [
                capability
                for capability in analysis.capabilities
                if capability != Capability.GENERAL_RESPONSE
            ]
            if not executable:
                return ValidatedResponse(
                    status=ResultStatus.SUCCESS,
                    answer="동국대학교의 공식 학사 안내와 nDRIMS 메뉴를 찾아드릴 수 있어요. 궁금한 내용을 조금 더 구체적으로 말씀해 주세요.",
                )

            # GENERAL_RESPONSE is an answer-writing capability, not a callable Tool.
            executable_analysis = analysis.model_copy(
                update={"capabilities": executable}
            )
            context_resolution = resolve_question_context(executable_analysis)
            plan = await self.planner(question, executable_analysis)
            assert_public_plan(plan)
            execution = await self.executor.execute(
                plan=plan,
                analysis=executable_analysis,
                context_resolution=context_resolution,
                tool_context=self.tool_context,
                # Anonymous public mode intentionally has no private context to
                # inject; rewrite is therefore identity-preserving here.
                question=question,
            )
            context = self.context_builder.build(execution)
            directive = self.fallback_policy.decide(
                context=context,
                execution=execution,
            )
            if directive.mode.value == "direct_response":
                return self.fallback_policy.finalize(
                    directive=directive,
                    context=context,
                )
            draft = await self.responder(question, context)
            return self.fallback_policy.finalize(
                directive=directive,
                context=context,
                draft=draft,
            )
        except Exception:
            # Browser clients receive a stable, non-technical response.  Detailed
            # errors remain in normal server logging/observability, never in chat.
            return self._unavailable()

    @staticmethod
    def _personal_data_boundary() -> ValidatedResponse:
        return ValidatedResponse(
            status=ResultStatus.SUCCESS,
            answer="개인 성적·수강·학적 정보는 이 공개 AI가 조회하지 않아요. 아래 nDRIMS에 직접 로그인하면 본인 정보를 안전하게 확인할 수 있습니다.",
            actions=[
                ActionReference(
                    action_id="open-ndrims",
                    action_type=ActionType.OPEN_URL,
                    label="nDRIMS 열기",
                    url=NDRIMS_MAIN_URL,
                )
            ],
            limitations=["개인 학사 정보는 공개 서비스에 저장하거나 AI로 처리하지 않습니다."],
        )

    @staticmethod
    def _unavailable() -> ValidatedResponse:
        return ValidatedResponse(
            status=ResultStatus.UNAVAILABLE,
            answer="지금은 공식 정보를 확인하지 못했어요. 잠시 후 다시 시도하거나 동국대학교 공식 안내를 확인해 주세요.",
            limitations=["확인 가능한 공식 근거가 없어서 답변을 보류했습니다."],
        )
