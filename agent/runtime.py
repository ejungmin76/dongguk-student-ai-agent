"""Small programmatic runtime around the root ADK agent."""

from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, InMemorySessionService
from google.genai import types

from .agent import root_agent
from .schemas import AgentResponse


APP_NAME = "dongguk_student_ai"


class StudentAgentRuntime:
    """Run turns while keeping conversation history in an ADK session."""

    def __init__(self, session_service: BaseSessionService | None = None) -> None:
        self.session_service = session_service or InMemorySessionService()
        self.runner = Runner(
            app_name=APP_NAME,
            agent=root_agent,
            session_service=self.session_service,
        )

    async def run_turn(
        self,
        *,
        user_id: str,
        session_id: str,
        message: str,
    ) -> AgentResponse:
        session = await self.session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
        if session is None:
            await self.session_service.create_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
            )

        final_response: AgentResponse | None = None
        async for event in self.runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=message)],
            ),
        ):
            if not event.is_final_response():
                continue

            if isinstance(event.output, dict):
                final_response = AgentResponse.model_validate(event.output)
                continue

            texts = [
                part.text
                for part in (event.content.parts if event.content else [])
                if part.text
            ]
            if texts:
                final_response = AgentResponse.model_validate_json("".join(texts))

        if final_response is None:
            raise RuntimeError("ADK run completed without a final structured response")
        return final_response
