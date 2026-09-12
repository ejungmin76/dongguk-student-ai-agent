"""Gemini classifier for references to a server-supplied recent history only."""

import json
import os

from google.adk.agents import Agent

from agent.schemas import FollowUpCandidate, FollowUpResolution


follow_up_resolver_agent = Agent(
    name="follow_up_resolver",
    model=os.getenv("GEMINI_AGENT_MODEL", "gemini-3.8-flash"),
    description="최근 대화가 필요한 후속 질문인지 분류한다.",
    instruction="""
입력의 current_question과 server_candidates만 보고 후속 질문 참조를 판정하라.
후속 참조가 필요 없으면 standalone을 반환한다. 하나의 후보와 명확히 연결되면
resolved와 그 turn_sequence 하나를 반환한다. 후보가 둘 이상이거나 확신할 수 없으면
clarification과 관련 후보 turn_sequence를 반환한다. 후보에 없는 대화, 학생 정보,
URL, 메뉴, 사실을 만들어내지 마라. 질문을 답하거나 다시 쓰지 마라.
""".strip(),
    output_schema=FollowUpResolution,
    output_key="follow_up_resolution",
    tools=[],
)


def build_follow_up_resolver_input(*, current_question: str, candidates: list[FollowUpCandidate]) -> str:
    return json.dumps({"current_question": current_question, "server_candidates": [candidate.model_dump(mode="json") for candidate in candidates]}, ensure_ascii=False)
