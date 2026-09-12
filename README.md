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
