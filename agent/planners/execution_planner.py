"""Gemini planner that emits a validated execution-plan intermediate form."""

import json
import os

from google.adk.agents import Agent

from agent.schemas import ContextResolution, ExecutionPlan, QuestionAnalysis


execution_planner_agent = Agent(
    name="execution_planner",
    model=os.getenv("GEMINI_AGENT_MODEL", "gemini-3.8-flash"),
    description="질문 분석과 문맥 상태를 실행 순서가 명시된 계획으로 변환한다.",
    instruction="""
입력 JSON의 question_analysis와 context_resolution을 실행 계획으로 변환하라.
답변을 생성하거나 실제 Tool을 호출하지 마라. step_id는 짧은 영문 snake_case로
만들고 steps는 실행 가능한 위상 순서로 배열하라.

허용 Capability와 문맥 규칙:
- student_profile: authenticated_student를 사용하고 primary_major와
  admission_year를 제공할 수 있다.
- academic_records: authenticated_student를 사용한다.
- current_schedule: authenticated_student를 사용하고 current_term을 제공할 수 있다.
- university_knowledge: 일반 학교 질문은 단독 실행할 수 있다. 개인 전공·입학연도
  기준 질문이면 해당 문맥을 제공하는 앞 단계에 의존한다.
- ndrims_menu: 공개 메뉴 레지스트리만 검색한다. 실제 nDRIMS 화면의 개인 정보는
  사용자가 해당 사이트에서 직접 로그인해 확인한다.
- general_response: 외부 문맥을 사용하지 않는다.

question_analysis.capabilities에 없는 Capability를 추가하지 마라. URL, 함수명,
SQL, Python 코드 또는 임의의 필드 이름을 만들지 마라. context_resolution의
missing_fields에 답변에 필수인 값이 있거나 question_analysis가 clarification을
요청하면 steps를 비우고 한국어 clarification_question을 하나만 작성하라.
deferred_fields는 앞 단계가 produces_context로 제공하도록 계획하라.
""".strip(),
    output_schema=ExecutionPlan,
    output_key="execution_plan",
    tools=[],
)

def build_execution_planner_input(
    *,
    question: str,
    analysis: QuestionAnalysis,
    context_resolution: ContextResolution,
) -> str:
    """Serialize trusted analysis inputs without building a natural-language prompt."""

    return json.dumps(
        {
            "question": question,
            "question_analysis": analysis.model_dump(mode="json"),
            "context_resolution": context_resolution.model_dump(mode="json"),
        },
        ensure_ascii=False,
    )
