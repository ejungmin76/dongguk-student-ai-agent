import json
import unittest

from pydantic import ValidationError

from agent.planners import (
    build_execution_planner_input,
    execution_planner_agent,
    resolve_question_context,
)
from agent.schemas import (
    Capability,
    ContextField,
    ContextNeed,
    ContextResolution,
    ContextSource,
    ExecutionPlan,
    ExecutionStep,
    IntentType,
    QuestionAnalysis,
)
from agent.validators import InvalidExecutionPlan, validate_execution_plan


def graduation_analysis() -> QuestionAnalysis:
    return QuestionAnalysis(
        intents=[IntentType.UNIVERSITY_KNOWLEDGE, IntentType.PERSONAL_ACADEMIC],
        capabilities=[
            Capability.STUDENT_PROFILE,
            Capability.UNIVERSITY_KNOWLEDGE,
        ],
        context_needs=[
            ContextNeed(
                field=ContextField.PRIMARY_MAJOR,
                source=ContextSource.STUDENT_PROFILE,
                reason="전공별 졸업요건 검색에 필요하다.",
            ),
            ContextNeed(
                field=ContextField.ADMISSION_YEAR,
                source=ContextSource.STUDENT_PROFILE,
                reason="입학연도별 적용 기준 확인에 필요하다.",
            ),
        ],
        rationale="개인 전공 기준의 졸업요건 질문이다.",
    )


def graduation_plan() -> ExecutionPlan:
    return ExecutionPlan(
        steps=[
            ExecutionStep(
                step_id="profile",
                capability=Capability.STUDENT_PROFILE,
                purpose="전공과 입학연도를 확인한다.",
                uses_context=[ContextField.AUTHENTICATED_STUDENT],
                produces_context=[
                    ContextField.PRIMARY_MAJOR,
                    ContextField.ADMISSION_YEAR,
                ],
            ),
            ExecutionStep(
                step_id="graduation_rules",
                capability=Capability.UNIVERSITY_KNOWLEDGE,
                purpose="적용되는 공식 졸업요건을 검색한다.",
                depends_on=["profile"],
                uses_context=[
                    ContextField.PRIMARY_MAJOR,
                    ContextField.ADMISSION_YEAR,
                ],
            ),
        ],
        rationale="프로필 결과를 공식 문서 검색 조건으로 사용한다.",
    )


class ContextResolverTests(unittest.TestCase):
    def test_profile_context_is_deferred_not_clarified(self):
        resolution = resolve_question_context(
            graduation_analysis(),
            session_fields=[ContextField.AUTHENTICATED_STUDENT],
        )

        self.assertEqual(
            set(resolution.deferred_fields),
            {ContextField.PRIMARY_MAJOR, ContextField.ADMISSION_YEAR},
        )
        self.assertEqual(resolution.missing_fields, [])

    def test_missing_session_context_is_reported(self):
        analysis = QuestionAnalysis(
            intents=[IntentType.NDRIMS_NAVIGATION],
            capabilities=[Capability.NDRIMS_MENU],
            context_needs=[
                ContextNeed(
                    field=ContextField.AUTHENTICATED_STUDENT,
                    source=ContextSource.SESSION,
                    reason="로그인된 학생 메뉴를 찾아야 한다.",
                )
            ],
            rationale="nDRIMS 메뉴 탐색 요청이다.",
        )

        resolution = resolve_question_context(analysis)

        self.assertEqual(
            resolution.missing_fields,
            [ContextField.AUTHENTICATED_STUDENT],
        )

    def test_ambiguous_service_requires_user_clarification(self):
        analysis = QuestionAnalysis(
            intents=[IntentType.NDRIMS_NAVIGATION],
            capabilities=[Capability.NDRIMS_MENU],
            context_needs=[
                ContextNeed(
                    field=ContextField.TARGET_SERVICE,
                    source=ContextSource.USER_CLARIFICATION,
                    reason="어떤 신청 메뉴를 찾는지 확인해야 한다.",
                )
            ],
            needs_clarification=True,
            clarification_question="어떤 신청을 말씀하시나요?",
            rationale="이동할 서비스가 불분명하다.",
        )

        resolution = resolve_question_context(analysis)

        self.assertEqual(resolution.missing_fields, [ContextField.TARGET_SERVICE])


class ExecutionPlanSchemaTests(unittest.TestCase):
    def test_dependencies_must_reference_an_earlier_step(self):
        with self.assertRaises(ValidationError):
            ExecutionPlan(
                steps=[
                    ExecutionStep(
                        step_id="rules",
                        capability=Capability.UNIVERSITY_KNOWLEDGE,
                        purpose="규정을 검색한다.",
                        depends_on=["profile"],
                    ),
                    ExecutionStep(
                        step_id="profile",
                        capability=Capability.STUDENT_PROFILE,
                        purpose="프로필을 조회한다.",
                    ),
                ],
                rationale="순서가 잘못된 계획이다.",
            )

    def test_clarification_plan_cannot_execute_steps(self):
        with self.assertRaises(ValidationError):
            ExecutionPlan(
                steps=[
                    ExecutionStep(
                        step_id="menu",
                        capability=Capability.NDRIMS_MENU,
                        purpose="메뉴를 검색한다.",
                    )
                ],
                needs_clarification=True,
                clarification_question="어떤 신청을 말씀하시나요?",
                rationale="신청 대상이 불분명하다.",
            )

    def test_ambiguous_question_can_stop_for_clarification(self):
        plan = ExecutionPlan(
            needs_clarification=True,
            clarification_question="어떤 신청을 말씀하시나요?",
            rationale="신청 대상이 불분명하다.",
        )

        self.assertEqual(plan.steps, [])


class ExecutionPlanValidatorTests(unittest.TestCase):
    def setUp(self):
        self.analysis = graduation_analysis()
        self.resolution = resolve_question_context(
            self.analysis,
            session_fields=[ContextField.AUTHENTICATED_STUDENT],
        )

    def test_valid_sequential_plan_passes(self):
        validate_execution_plan(
            graduation_plan(),
            analysis=self.analysis,
            context_resolution=self.resolution,
        )

    def test_unrequested_capability_is_rejected(self):
        plan = graduation_plan()
        plan.steps.append(
            ExecutionStep(
                step_id="menu",
                capability=Capability.NDRIMS_MENU,
                purpose="요청하지 않은 메뉴를 검색한다.",
                uses_context=[ContextField.AUTHENTICATED_STUDENT],
            )
        )

        with self.assertRaises(InvalidExecutionPlan):
            validate_execution_plan(
                plan,
                analysis=self.analysis,
                context_resolution=self.resolution,
            )

    def test_fabricated_context_output_is_rejected(self):
        plan = graduation_plan()
        plan.steps[0].produces_context.append(ContextField.CURRENT_TERM)

        with self.assertRaises(InvalidExecutionPlan):
            validate_execution_plan(
                plan,
                analysis=self.analysis,
                context_resolution=self.resolution,
            )

    def test_missing_dependency_makes_context_unavailable(self):
        plan = graduation_plan()
        plan.steps[1].depends_on = []

        with self.assertRaises(InvalidExecutionPlan):
            validate_execution_plan(
                plan,
                analysis=self.analysis,
                context_resolution=self.resolution,
            )

    def test_ready_plan_cannot_ignore_missing_context(self):
        analysis = QuestionAnalysis(
            intents=[IntentType.NDRIMS_NAVIGATION],
            capabilities=[Capability.NDRIMS_MENU],
            context_needs=[
                ContextNeed(
                    field=ContextField.AUTHENTICATED_STUDENT,
                    source=ContextSource.SESSION,
                    reason="로그인된 학생 메뉴를 확인해야 한다.",
                )
            ],
            rationale="nDRIMS 메뉴 탐색 요청이다.",
        )
        resolution = resolve_question_context(analysis)
        plan = ExecutionPlan(
            steps=[
                ExecutionStep(
                    step_id="menu",
                    capability=Capability.NDRIMS_MENU,
                    purpose="메뉴를 찾는다.",
                    uses_context=[ContextField.AUTHENTICATED_STUDENT],
                )
            ],
            rationale="메뉴 검색 계획이다.",
        )

        with self.assertRaises(InvalidExecutionPlan):
            validate_execution_plan(
                plan,
                analysis=analysis,
                context_resolution=resolution,
            )


class ExecutionPlannerAgentTests(unittest.TestCase):
    def test_planner_uses_structured_output_without_tools(self):
        self.assertEqual(execution_planner_agent.output_schema, ExecutionPlan)
        self.assertEqual(execution_planner_agent.output_key, "execution_plan")
        self.assertEqual(execution_planner_agent.tools, [])

    def test_planner_input_is_structured_json(self):
        payload = build_execution_planner_input(
            question="나 컴ㅁ에인데 우리 전공졸업학점 몇임?",
            analysis=graduation_analysis(),
            context_resolution=ContextResolution(
                resolved_fields=[ContextField.AUTHENTICATED_STUDENT],
                deferred_fields=[
                    ContextField.PRIMARY_MAJOR,
                    ContextField.ADMISSION_YEAR,
                ],
            ),
        )

        restored = json.loads(payload)

        self.assertEqual(restored["question_analysis"]["capabilities"][0], "student_profile")
        self.assertEqual(
            restored["context_resolution"]["resolved_fields"],
            ["authenticated_student"],
        )
