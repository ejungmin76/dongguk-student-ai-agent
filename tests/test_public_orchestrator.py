from unittest import IsolatedAsyncioTestCase

from google.adk.tools import FunctionTool

from agent.executors import MultiToolExecutor
from agent.orchestrator import PublicAgentOrchestrator
from agent.schemas import (
    ActionType,
    Capability,
    ExecutionPlan,
    ExecutionStep,
    IntentType,
    QuestionAnalysis,
    ResponseDraft,
    ResultStatus,
)


class FakeRegistry:
    def tool_for_capability(self, capability, *, context):
        del context
        if capability != Capability.NDRIMS_MENU:
            return None

        async def find_ndrims_menu(question: str):
            """Return a server-registered menu result for an integration test."""
            return {
                "status": "success",
                "data": {
                    "candidates": [
                        {
                            "menu_key": "dormitory-application",
                            "title": "기숙사 신청",
                            "breadcrumb": ["학생생활", "기숙사 신청"],
                        }
                    ],
                    "requires_user_selection": False,
                },
                "sources": [
                    {
                        "source_id": "ndrims-student-menu-registry",
                        "source_type": "service_registry",
                        "title": "동국대학교 nDRIMS 학생 메뉴",
                        "url": "https://ndrims.dongguk.edu/main/main.clx",
                    }
                ],
                "actions": [
                    {
                        "action_id": "dormitory-application",
                        "action_type": "open_url",
                        "label": "학생생활 > 기숙사 신청",
                        "url": "https://ndrims.dongguk.edu/main/main.clx",
                    }
                ],
            }

        return FunctionTool(find_ndrims_menu)


class PublicOrchestratorTests(IsolatedAsyncioTestCase):
    async def test_public_menu_question_runs_tool_and_returns_verified_action(self):
        async def analyze(question):
            self.assertIn("기숙사", question)
            return QuestionAnalysis(
                intents=[IntentType.NDRIMS_NAVIGATION],
                capabilities=[Capability.NDRIMS_MENU],
                rationale="등록된 메뉴를 찾아야 한다.",
            )

        async def plan(question, analysis):
            self.assertEqual(analysis.capabilities, [Capability.NDRIMS_MENU])
            return ExecutionPlan(
                steps=[
                    ExecutionStep(
                        step_id="menu",
                        capability=Capability.NDRIMS_MENU,
                        purpose="검증된 메뉴를 찾는다.",
                    )
                ],
                rationale="공개 메뉴 검색만 실행한다.",
            )

        async def respond(question, context):
            self.assertEqual(context.status, ResultStatus.SUCCESS)
            self.assertEqual(len(context.actions), 1)
            return ResponseDraft(
                status=ResultStatus.SUCCESS,
                answer="기숙사 신청은 등록된 nDRIMS 메뉴에서 열 수 있어요.",
                source_ids=["ndrims-student-menu-registry"],
                action_ids=["dormitory-application"],
            )

        orchestrator = PublicAgentOrchestrator(
            analyzer=analyze,
            planner=plan,
            responder=respond,
            executor=MultiToolExecutor(registry=FakeRegistry()),
        )

        result = await orchestrator.run(question="기숙사 신청 메뉴 찾아줘")

        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertEqual(result.actions[0].action_type, ActionType.OPEN_URL)
        self.assertEqual(str(result.actions[0].url), "https://ndrims.dongguk.edu/main/main.clx")

    async def test_personal_question_cannot_reach_an_executor(self):
        executor_called = False

        async def analyze(question):
            return QuestionAnalysis(
                intents=[IntentType.PERSONAL_ACADEMIC],
                capabilities=[Capability.ACADEMIC_RECORDS],
                rationale="개인 성적이 필요하다.",
            )

        async def planner(question, analysis):
            raise AssertionError("private questions must not be planned")

        async def respond(question, context):
            raise AssertionError("private questions must not use the response model")

        class NeverExecutor:
            async def execute(self, **kwargs):
                nonlocal executor_called
                executor_called = True
                raise AssertionError("private questions must not execute a tool")

        orchestrator = PublicAgentOrchestrator(
            analyzer=analyze,
            planner=planner,
            responder=respond,
            executor=NeverExecutor(),
        )

        result = await orchestrator.run(question="내 평점 알려줘")

        self.assertFalse(executor_called)
        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertEqual(result.actions[0].action_id, "open-ndrims")
        self.assertIn("조회하지 않아요", result.answer)
