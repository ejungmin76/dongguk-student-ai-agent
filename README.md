# dongguk-student-ai-agent

동국대학교 학생 맞춤형 AI Agent PoC입니다.

## 요구 사항

- Python 3.12 이상
- Django 5.2

## Windows 로컬 실행

```powershell
cd C:\Users\ejung\Desktop\dongguk-student-ai-agent
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements\development.txt
python manage.py migrate
python manage.py runserver
```

확인 주소:

- Health check: http://127.0.0.1:8000/health/
- Django Admin: http://127.0.0.1:8000/admin/

Health check 응답:

```json
{
  "status": "ok",
  "service": "dongguk-student-ai-agent"
}
```

## 테스트

```powershell
python manage.py test --settings=config.settings.test
```

## 설정 구조

- `config.settings.base`: 공통 설정
- `config.settings.development`: 로컬 개발 설정
- `config.settings.test`: 자동 테스트 설정

민감한 값은 커밋하지 않습니다. 필요한 환경변수 이름만 `.env.example`에 기록합니다.

## 아키텍처

코드 배치, 계층별 책임, 의존 방향과 MCP 적용 경계는
[`docs/architecture.md`](docs/architecture.md)에 정의되어 있습니다. 중요한 구조 결정은
[`docs/decisions/`](docs/decisions/)에 ADR로 기록합니다.

Tool과 Agent가 공유하는 상태, 오류, 출처, Action, 결과 envelope 규격은
[`docs/common-schemas.md`](docs/common-schemas.md)에 정의되어 있습니다.

Google ADK + Gemini Agent의 초기 실행 방법과 현재 제한 사항은
[`docs/adk-agent-bootstrap.md`](docs/adk-agent-bootstrap.md)에 정의되어 있습니다.

자연어 질문을 상위 의도, 필요한 문맥, 허용 기능으로 변환하는 계약은
[`docs/question-analysis.md`](docs/question-analysis.md)에 정의되어 있습니다.

질문 문맥을 확인하고 검증 가능한 실행계획 IR로 변환하는 방식은
[`docs/context-resolver-planner.md`](docs/context-resolver-planner.md)에 정의되어 있습니다.

검증된 Capability를 요청별 ADK FunctionTool에 연결하는 방식은
[`docs/adk-tool-registry.md`](docs/adk-tool-registry.md)에 정의되어 있습니다.

여러 Tool의 의존 그래프, 병렬·순차 실행과 부분 실패 정책은
[`docs/multi-tool-execution.md`](docs/multi-tool-execution.md)에 정의되어 있습니다.

여러 Tool 결과를 답변용 최소 컨텍스트로 정규화하는 방식은
[`docs/context-builder.md`](docs/context-builder.md)에 정의되어 있습니다.

안전한 Context를 짧고 친절한 한국어 답변 초안으로 바꾸는 방식은
[`docs/response-agent.md`](docs/response-agent.md)에 정의되어 있습니다.

Gemini 초안의 사실·출처·Action을 서버에서 검증하는 방식은
[`docs/response-validator.md`](docs/response-validator.md)에 정의되어 있습니다.

Tool 실패·부분 성공·재질문의 안전한 처리 정책은
[`docs/fallback-policy.md`](docs/fallback-policy.md)에 정의되어 있습니다.

대화 세션 보존 범위와 후속 질문 참조 검증 방식은
[`docs/conversation-context.md`](docs/conversation-context.md)에 정의되어 있습니다.

질의별 문맥 보강과 원문 추적 규칙은
[`docs/query-rewrite.md`](docs/query-rewrite.md)에 정의되어 있습니다.

웹 UI가 사용하는 인증·세션 기반 Chat API 계약은
[`docs/agent-chat-api.md`](docs/agent-chat-api.md)에 정의되어 있습니다.

실시간 진행 상태·근거·Action 전달과 재연결 규칙은
[`docs/agent-chat-streaming.md`](docs/agent-chat-streaming.md)에 정의되어 있습니다.

Next.js 랜딩 페이지와 플로팅 AI Assistant 위젯 실행 방법은
[`docs/nextjs-demo-ui.md`](docs/nextjs-demo-ui.md)에 정의되어 있습니다.
