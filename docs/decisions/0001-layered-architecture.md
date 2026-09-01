# ADR 0001: Layered architecture for the PoC

- Status: Accepted
- Date: 2026-09-01

## Context

PoC는 Django, PostgreSQL/pgvector, Google ADK, Gemini를 함께 사용하며 후반에 MCP를 적용한다. Agent 코드가 Django ORM이나 MCP 구현에 직접 결합되면 학사 API 전환과 framework 교체 비용이 커진다.

## Decision

호출 방향을 `entrypoint -> agent -> tool -> service -> repository -> model`로 제한한다. 업무 규칙은 Service, 영속성은 Repository, Agent capability 계약은 Tool이 소유한다. MCP는 Phase 8의 interface adapter로 추가하고 기존 Service와 Repository를 재사용한다.

도메인 Django 앱은 실제 구현 Phase가 시작될 때 생성한다. 현재는 Agent와 Tool의 안정적인 상위 패키지 경계만 미리 만든다.

## Consequences

- Agent framework와 DB 구현을 독립적으로 테스트하고 교체하기 쉬워진다.
- 단순 기능도 여러 계층에 걸칠 수 있으므로 파일 수가 늘어난다.
- 계층을 건너뛰는 빠른 구현을 code review와 architecture test에서 차단해야 한다.
