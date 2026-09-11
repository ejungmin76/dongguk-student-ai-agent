"""Google ADK entry point discovered by ``adk run agent``."""

import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import Agent

from .schemas import AgentResponse


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


root_agent = Agent(
    name="dongguk_student_agent",
    model=os.getenv("GEMINI_AGENT_MODEL", "gemini-3.8-flash"),
    description="동국대학교 학생의 질문을 안전하게 처리하는 한국어 AI 에이전트",
    instruction="""
당신은 동국대학교 학생 지원 AI 에이전트의 초기 실행 골격이다.
항상 한국어로 간결하고 명확하게 답한다.

현재 단계에는 학교 지식, 학생 학사 정보, nDRIMS 메뉴를 조회하는 도구가 연결되어
있지 않다. 따라서 학교별 규정, 학생별 정보, 메뉴 경로를 추측하거나 만들어내지
말고 status를 unavailable로 반환한다. 사용자의 의도가 불명확하여 한 가지 질문이
필요할 때만 status를 clarification으로 반환하고 follow_up_question을 작성한다.
일반적인 인사나 이 에이전트의 역할처럼 외부 사실이 필요 없는 요청에는
status를 success로 반환한다.
""".strip(),
    output_schema=AgentResponse,
    output_key="agent_response",
    tools=[],
)
