# Google ADK + Gemini Agent 초기 구성

## 범위

Issue #21에서는 Google ADK가 Gemini를 호출하고 Pydantic 형식으로 응답하는
최소 실행 골격만 구성한다. 학사·학교 지식·nDRIMS 메뉴 Tool 연결과 Tool 선택은
후속 이슈에서 진행한다.

## 구성

- `agent/agent.py`: ADK가 발견하는 `root_agent`
- `agent/schemas/response.py`: 초기 구조화 응답 계약
- `agent/runtime.py`: 메모리 세션을 이용한 프로그램 실행 진입점
- 기본 모델: `gemini-3.8-flash`
- 응답 상태: `success`, `partial`, `clarification`, `unavailable`

Gemini Developer API의 response schema는 JSON Schema의
`additionalProperties`를 받지 않으므로 이 응답 모델에 한해 알 수 없는 출력
필드를 무시한다. 정의된 필드의 타입·필수값·상태 조합은 Pydantic으로 계속
검증한다.

현재 Agent에는 Tool이 없으므로 학교 규정, 개인 학사 정보, nDRIMS 경로를
추측하지 않는다. 해당 질문에는 `unavailable`을 반환하도록 instruction에
명시했다.

## 환경변수

`.env`에 다음 값을 설정한다.

```dotenv
GOOGLE_API_KEY=발급받은_Gemini_API_Key
GEMINI_AGENT_MODEL=gemini-3.8-flash
```

키는 `.env`에만 두며 Git에 커밋하지 않는다.

## 로컬 실행

프로젝트 루트에서 가상환경을 활성화한 뒤 실행한다.

```powershell
adk run agent
```

한 번만 질문하고 종료하려면 다음처럼 실행한다.

```powershell
adk run agent "안녕, 어떤 도움을 줄 수 있어?"
```

이 단계의 `InMemorySessionService`는 실행 중 대화 문맥만 유지한다. 프로세스를
재시작하면 세션이 사라지므로 영속 세션 저장소는 Context 단계에서 별도로
구현한다.

## 검증

```powershell
python manage.py test tests.test_adk_agent --settings=config.settings.test
python manage.py test --settings=config.settings.test
python manage.py check
```

실제 API smoke test는 동일한 세션에 두 번 질문해 두 번째 응답이 첫 번째 대화를
참조하는지 확인한다. 이 테스트는 API 요금이 발생하므로 자동 테스트에는 넣지
않는다.
