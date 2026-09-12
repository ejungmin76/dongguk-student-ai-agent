"""ADK Response Agent that writes concise Korean from safe response context."""

import json
import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, InMemorySessionService
from google.genai import types

from agent.schemas import ResponseContext, ResponseDraft


load_dotenv(Path(__file__).resolve().parents[2] / ".env")

APP_NAME = "dongguk_student_response"


response_agent = Agent(
    name="response_agent",
    model=os.getenv("GEMINI_AGENT_MODEL", "gemini-3.8-flash"),
    description="검증 가능한 학생·공식 근거를 짧고 친절한 한국어 답변으로 정리한다.",
    instruction="""
입력 JSON의 response_context에 있는 정보만 사용해 학생 질문에 한국어로 답하라.
당신의 역할은 사실 판단이 아니라 검증된 사실을 읽기 좋은 문장으로 정리하는 것이다.

글쓰기 원칙:
- 첫 문장에서 질문의 결론이나 현재 상태를 바로 말한다.
- 기본적으로 자연스러운 2~4문장, 500자 이내의 짧은 문단으로 작성한다.
- 표, Markdown 제목, 목록, 장황한 인사말, 출처 URL을 answer에 쓰지 않는다.
- 개인 학사 정보는 "현재" 또는 "내 학사 정보"처럼 표현하고, 학교 규정·일정은
  "공식 문서 기준"처럼 구분한다.
- Context에 없는 수치, 날짜, 메뉴 경로, 규정, URL 또는 계산 결과를 만들지 않는다.
- context.status가 partial/unavailable이거나 context.truncated가 true이면 확정할 수
  없는 범위를 limitations에 짧게 밝히고 answer에서도 자연스럽게 한 번 언급한다.
- 졸업 가능 여부는 영역별 요건·필수과목까지 주어지지 않았다면 단정하지 않는다.
- Action이 있으면 질문과 직접 관련 있는 action_id만 action_ids에 넣는다. 메뉴 이동을
  실행하거나 URL을 만들어서는 안 된다.

출처와 상태:
- 공식 문서에 근거한 내용은 citation_options에 있는 source_id만 source_ids에 넣는다.
- source_id와 action_id는 입력 목록에서 정확히 복사하며 새 값을 만들지 않는다.
- status는 response_context.status와 정확히 같게 반환한다.
- clarification일 때만 follow_up_question을 한 문장으로 작성한다. 그 외에는 null이다.

후속 서버 Validator가 사실, 출처와 Action을 검증한다. 입력에 없는 사실을 그럴듯하게
보완하지 말고, 부족한 경우에는 제한을 명확히 설명하라.
""".strip(),
    output_schema=ResponseDraft,
    output_key="response_draft",
    tools=[],
)


def build_response_agent_input(*, question: str, context: ResponseContext) -> str:
    """Serialize only answer-safe facts and ID allowlists for the Response Agent."""

    return json.dumps(
        {
            "question": question,
            "response_context": {
                "status": context.status,
                "items": [item.model_dump(mode="json") for item in context.items],
                "errors": [error.model_dump(mode="json") for error in context.errors],
                "truncated": context.truncated,
                "omissions": [
                    omission.model_dump(mode="json") for omission in context.omissions
                ],
            },
            "citation_options": [
                {
                    "source_id": source.source_id,
                    "title": source.title,
                    "page": source.page,
                    "effective_at": source.effective_at,
                }
                for source in context.sources
            ],
            "action_options": [
                {
                    "action_id": action.action_id,
                    "label": action.label,
                }
                for action in context.actions
            ],
        },
        ensure_ascii=False,
        default=str,
    )


class ResponseAgentRuntime:
    """Run the no-tool Response Agent and parse its structured draft."""

    def __init__(self, session_service: BaseSessionService | None = None) -> None:
        self.session_service = session_service or InMemorySessionService()
        self.runner = Runner(
            app_name=APP_NAME,
            agent=response_agent,
            session_service=self.session_service,
            auto_create_session=True,
        )

    async def generate(
        self,
        *,
        question: str,
        context: ResponseContext,
        user_id: str = "response-user",
        session_id: str | None = None,
    ) -> ResponseDraft:
        """Return an unvalidated model draft; Issue #29 performs final grounding."""

        session_id = session_id or str(uuid4())
        final_draft: ResponseDraft | None = None
        async for event in self.runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(
                role="user",
                parts=[
                    types.Part(
                        text=build_response_agent_input(
                            question=question,
                            context=context,
                        )
                    )
                ],
            ),
        ):
            if not event.is_final_response():
                continue
            if isinstance(event.output, dict):
                final_draft = ResponseDraft.model_validate(event.output)
                continue

            texts = [
                part.text
                for part in (event.content.parts if event.content else [])
                if part.text
            ]
            if texts:
                final_draft = ResponseDraft.model_validate_json("".join(texts))

        if final_draft is None:
            raise RuntimeError("response agent completed without a structured draft")
        return final_draft
