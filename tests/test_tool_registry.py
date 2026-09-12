import inspect

from django.test import SimpleTestCase

from agent.executors import (
    ToolCallingAgentBuildError,
    build_single_tool_calling_agent,
)
from agent.schemas import (
    Capability,
    ContextField,
    ContextResolution,
    ExecutionPlan,
    ExecutionStep,
    IntentType,
    QuestionAnalysis,
)
from agent.tool_registry import (
    ToolAuthorizationError,
    ToolBuildContext,
    default_tool_registry,
)
from tools.academic import AcademicToolActor


def single_capability_analysis(capability: Capability) -> QuestionAnalysis:
    intent = {
        Capability.STUDENT_PROFILE: IntentType.PERSONAL_ACADEMIC,
        Capability.ACADEMIC_RECORDS: IntentType.PERSONAL_ACADEMIC,
        Capability.CURRENT_SCHEDULE: IntentType.PERSONAL_ACADEMIC,
        Capability.UNIVERSITY_KNOWLEDGE: IntentType.UNIVERSITY_KNOWLEDGE,
        Capability.NDRIMS_MENU: IntentType.NDRIMS_NAVIGATION,
        Capability.GENERAL_RESPONSE: IntentType.GENERAL_CONVERSATION,
    }[capability]
    return QuestionAnalysis(
        intents=[intent],
        capabilities=[capability],
        rationale="하나의 기능만 필요한 대표 질문이다.",
    )


def single_capability_plan(capability: Capability) -> ExecutionPlan:
    private = capability in {
        Capability.STUDENT_PROFILE,
        Capability.ACADEMIC_RECORDS,
        Capability.CURRENT_SCHEDULE,
        Capability.NDRIMS_MENU,
    }
    return ExecutionPlan(
        steps=[
            ExecutionStep(
                step_id="lookup",
                capability=capability,
                purpose="요청된 정보를 조회한다.",
                uses_context=(
                    [ContextField.AUTHENTICATED_STUDENT] if private else []
                ),
                produces_context=(
                    [ContextField.PRIMARY_MAJOR, ContextField.ADMISSION_YEAR]
                    if capability == Capability.STUDENT_PROFILE
                    else []
                ),
            )
        ],
        rationale="단일 조회 계획이다.",
    )


class ToolRegistryTests(SimpleTestCase):
    def setUp(self):
        self.authenticated_context = ToolBuildContext(
            actor=AcademicToolActor(student_number="MOCK-2026-008")
        )

    def test_registry_covers_every_capability_once(self):
        definitions = default_tool_registry.definitions

        self.assertEqual(
            {definition.capability for definition in definitions},
            set(Capability),
        )

    def test_each_external_capability_maps_to_expected_tool(self):
        expected = {
            Capability.STUDENT_PROFILE: "get_student_profile",
            Capability.ACADEMIC_RECORDS: "get_academic_records",
            Capability.CURRENT_SCHEDULE: "get_current_schedule",
            Capability.UNIVERSITY_KNOWLEDGE: "search_university_knowledge",
            Capability.NDRIMS_MENU: "find_ndrims_menu",
        }

        for capability, tool_name in expected.items():
            with self.subTest(capability=capability):
                tool = default_tool_registry.tool_for_capability(
                    capability,
                    context=self.authenticated_context,
                )
                self.assertEqual(tool.name, tool_name)
                self.assertTrue(tool.description)
                self.assertTrue(inspect.iscoroutinefunction(tool.func))

    def test_generated_function_schemas_keep_typed_parameters(self):
        knowledge_tool = default_tool_registry.tool_for_capability(
            Capability.UNIVERSITY_KNOWLEDGE,
            context=ToolBuildContext(),
        )

        parameters = inspect.signature(knowledge_tool.func).parameters

        self.assertEqual(list(parameters), [
            "question",
            "effective_year",
            "effective_on",
            "top_k",
        ])
        self.assertEqual(parameters["top_k"].default, 5)

    def test_private_capability_is_not_exposed_without_authentication(self):
        with self.assertRaises(ToolAuthorizationError):
            default_tool_registry.tool_for_capability(
                Capability.ACADEMIC_RECORDS,
                context=ToolBuildContext(),
            )

    def test_public_knowledge_tool_is_available_without_student_identity(self):
        tool = default_tool_registry.tool_for_capability(
            Capability.UNIVERSITY_KNOWLEDGE,
            context=ToolBuildContext(),
        )

        self.assertEqual(tool.name, "search_university_knowledge")

    def test_general_response_does_not_create_a_function_tool(self):
        tool = default_tool_registry.tool_for_capability(
            Capability.GENERAL_RESPONSE,
            context=ToolBuildContext(),
        )

        self.assertIsNone(tool)


class SingleToolCallingAgentTests(SimpleTestCase):
    def setUp(self):
        self.resolution = ContextResolution(
            resolved_fields=[ContextField.AUTHENTICATED_STUDENT]
        )
        self.tool_context = ToolBuildContext(
            actor=AcademicToolActor(student_number="MOCK-2026-008")
        )

    def test_plan_exposes_only_selected_profile_tool(self):
        capability = Capability.STUDENT_PROFILE
        agent = build_single_tool_calling_agent(
            plan=single_capability_plan(capability),
            analysis=single_capability_analysis(capability),
            context_resolution=self.resolution,
            tool_context=self.tool_context,
        )

        self.assertEqual([tool.name for tool in agent.tools], ["get_student_profile"])
        self.assertEqual(agent.mode, "chat")

    def test_plan_exposes_only_selected_ndrims_tool(self):
        capability = Capability.NDRIMS_MENU
        agent = build_single_tool_calling_agent(
            plan=single_capability_plan(capability),
            analysis=single_capability_analysis(capability),
            context_resolution=self.resolution,
            tool_context=self.tool_context,
        )

        self.assertEqual([tool.name for tool in agent.tools], ["find_ndrims_menu"])

    def test_multi_tool_plan_is_deferred_to_later_executor_issue(self):
        plan = ExecutionPlan(
            steps=[
                ExecutionStep(
                    step_id="records",
                    capability=Capability.ACADEMIC_RECORDS,
                    purpose="성적을 조회한다.",
                    uses_context=[ContextField.AUTHENTICATED_STUDENT],
                ),
                ExecutionStep(
                    step_id="schedule",
                    capability=Capability.CURRENT_SCHEDULE,
                    purpose="시간표를 조회한다.",
                    uses_context=[ContextField.AUTHENTICATED_STUDENT],
                ),
            ],
            rationale="두 조회가 모두 필요하다.",
        )
        analysis = QuestionAnalysis(
            intents=[IntentType.PERSONAL_ACADEMIC],
            capabilities=[Capability.ACADEMIC_RECORDS, Capability.CURRENT_SCHEDULE],
            rationale="두 개인 학사 기능이 필요하다.",
        )

        with self.assertRaises(ToolCallingAgentBuildError):
            build_single_tool_calling_agent(
                plan=plan,
                analysis=analysis,
                context_resolution=self.resolution,
                tool_context=self.tool_context,
            )
