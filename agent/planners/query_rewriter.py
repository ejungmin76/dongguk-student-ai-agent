"""Gemini chooses allowed rewrite context; the server builds the query text."""

import json
import os

from google.adk.agents import Agent

from agent.schemas import ContextField, QueryRewriteProposal, QueryTarget


query_rewriter_agent = Agent(
    name="query_rewriter",
    model=os.getenv("GEMINI_AGENT_MODEL", "gemini-3.8-flash"),
    description="질의 대상별로 허용된 문맥 사용 여부만 선택한다.",
    instruction="""
원문 질문의 의미를 바꾸거나 답변하지 마라. rewritten query나 학생 정보 값,
전공명, 학번, URL, 메뉴명을 출력하지 마라. target에 맞고 입력의
available_context_fields에 실제로 있는 필드만 context_fields로 선택하라.
개인 학사 조회는 문맥 값을 검색 문장에 넣지 않는다는 점을 고려하라.
후속 대화 참조가 필요하면 include_follow_up_reference를 true로 하되, 참조 내용은
출력하지 마라. 확신이 없으면 context_fields를 비워 원문을 그대로 사용하라.
""".strip(),
    output_schema=QueryRewriteProposal,
    output_key="query_rewrite_proposal",
    tools=[],
)


def build_query_rewriter_input(
    *,
    original_query: str,
    target: QueryTarget,
    available_context_fields: list[ContextField],
    has_validated_follow_up: bool,
) -> str:
    """Send field names, never field values or free-text conversation history."""
    return json.dumps(
        {
            "original_query": original_query,
            "target": target.value,
            "available_context_fields": [field.value for field in available_context_fields],
            "has_validated_follow_up": has_validated_follow_up,
        },
        ensure_ascii=False,
    )
