# PoC architecture

## 목적

이 문서는 동국대학교 학생 맞춤형 AI Agent PoC의 코드 배치, 계층별 책임, 의존 방향을 정의한다. 새 기능은 이 규칙을 기본값으로 따르며 예외가 필요하면 별도 Architecture Decision Record(ADR)에 이유를 남긴다.

## 전체 호출 흐름

```text
Django API / Admin / Command
            |
            v
Google ADK Agent (plan, execute, respond, validate)
            |
            v
Tool facade (contract and capability boundary)
            |
            v
Domain service (business rules and calculations)
            |
            v
Repository (data access interface and adapter)
            |
            v
Django ORM model -> PostgreSQL / pgvector
```

응답은 위 흐름의 역순으로 반환한다. 상위 계층은 아래 계층을 호출할 수 있지만 아래 계층이 상위 계층을 호출하면 안 된다.

## 디렉터리 책임

```text
apps/
  core/                  health check와 공통 Django 기반
  academic/              학생, 성적, 수강 도메인(Phase 1에서 생성)
  knowledge/             문서와 검색 도메인(Phase 2에서 생성)
  ndrims/                로그인된 nDRIMS 메뉴 지도 도메인(Phase 4에서 생성)
  conversation/          세션과 대화 문맥 도메인(Phase 4에서 생성)

agent/
  schemas/               Pydantic 기반 입력, 계획, 문맥, 응답 계약
  planners/              질문을 capability와 실행 계획으로 변환
  executors/             Tool을 병렬 또는 순차 실행
  responders/            검증 가능한 데이터로 자연어 답변 생성
  validators/            개인 사실, 출처, 계산, Action 검증

tools/
  academic/              학사 Service를 Agent capability로 노출
  knowledge/             RAG Service를 Agent capability로 노출
  ndrims/                nDRIMS 메뉴 검색 Service를 Agent capability로 노출

config/                  Django 실행 및 환경별 설정
docs/                    아키텍처와 주요 결정 기록
```

각 Django 도메인 앱은 필요할 때 다음 내부 구조를 사용한다.

```text
apps/<domain>/
  models.py              영속 데이터 구조
  schemas.py             도메인 입출력 DTO
  services/              업무 규칙과 유스케이스
  repositories/          데이터 접근 계약과 Django ORM 구현
  tests/                 도메인 단위 및 통합 테스트
```

미래에 사용할 가능성만으로 빈 Django 앱을 미리 만들지는 않는다. 해당 Phase가 시작될 때 앱을 만들고 `INSTALLED_APPS`에 등록한다.

## 계층별 규칙

### API와 Django 진입점

- HTTP 형식, 인증된 사용자, 상태 코드를 처리한다.
- 비즈니스 규칙이나 ORM 조회를 직접 작성하지 않는다.
- Agent 또는 명시적인 Service 유스케이스를 호출한다.

### Agent

- 자연어 이해, 계획, Tool 실행 조정, 답변 생성과 검증을 담당한다.
- Django model, ORM query, DB credential을 직접 사용하지 않는다.
- 개인 데이터는 Tool이 반환한 최소 필드만 사용한다.
- 정확한 계산과 권한 판단은 Service 결과를 따른다.

### Tool

- Agent가 사용할 수 있는 안정적인 capability 계약이다.
- 입력과 출력을 Pydantic schema로 검증한다.
- 얇은 adapter로 유지하고 업무 규칙은 Service에 위임한다.
- ORM을 직접 호출하지 않는다.

### Service

- 학점 계산, 문서 상태, Action 검증 같은 업무 규칙을 담당한다.
- Agent나 Tool framework에 의존하지 않는다.
- 데이터가 필요하면 Repository 계약을 통해 요청한다.

### Repository

- 조회, 저장, 필터링 등 영속성 접근만 담당한다.
- Django ORM model을 DTO 또는 domain schema로 변환한다.
- Agent, Tool, HTTP 응답 형식을 알지 못한다.

### Model

- PostgreSQL 테이블, 관계, 제약조건을 표현한다.
- 상위 계층을 import하지 않는다.

## 허용 및 금지 의존성

허용:

```text
API -> Agent -> Tool -> Service -> Repository -> Model
Admin/Command -> Service -> Repository -> Model
```

금지:

```text
Model -> Repository/Service/Tool/Agent
Repository -> Service/Tool/Agent
Service -> Tool/Agent
Tool -> Django model 직접 접근
Agent -> Repository 또는 Django model 직접 접근
```

공통 schema 때문에 순환 import가 생기면 schema를 더 낮은 계층 또는 해당 도메인으로 이동한다. `core`를 모든 코드의 임시 보관소로 사용하지 않는다.

## ADK와 MCP 경계

Phase 3까지는 ADK Tool이 기존 Service를 직접 호출한다.

```text
Google ADK -> ADK Tool adapter -> Service -> Repository
```

Phase 8에서는 Service와 Repository를 변경하지 않고 인터페이스 adapter만 교체한다.

```text
Google ADK -> MCP Client
                 |
                 v
University MCP Server -> Service -> Repository
```

- MCP Server는 새 비즈니스 로직을 소유하지 않는다.
- MCP Tool schema는 기존 Tool/Pydantic 계약을 재사용하거나 명시적으로 변환한다.
- 인증, 권한, 데이터 최소화는 MCP 밖으로 밀어내지 않고 서버 측 Service 경계에서 유지한다.
- MCP 장애 시에도 Service와 Repository 단위 테스트는 독립적으로 실행 가능해야 한다.

## 새 기능 배치 예시

`내 누적 평점 알려줘` 기능은 다음 위치에 나뉜다.

```text
agent/planners/                          성적 조회 capability 선택
tools/academic/                          get_academic_records Tool 계약
apps/academic/services/                  학사 조회 유스케이스
apps/academic/repositories/              Django ORM 조회
apps/academic/models.py                  성적과 이수 데이터 구조
```

## 검증 방법

```powershell
python -m unittest tests.test_architecture
python manage.py check
python manage.py test
```

구조 변경 시 위 검사와 함께 다음을 수동 확인한다.

- Agent가 ORM을 직접 import하지 않는가?
- Tool 안에 학점 계산이나 권한 규칙이 들어가지 않았는가?
- Repository가 HTTP 또는 LLM 응답 형식을 반환하지 않는가?
- 새 adapter를 추가해도 Service를 재사용할 수 있는가?
