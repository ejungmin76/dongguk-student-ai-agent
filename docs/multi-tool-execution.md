# Multi-Tool 병렬·순차 실행

## 실행 책임

Gemini는 질문을 `Capability`와 `ExecutionPlan`으로 구조화하지만 실제 실행 순서는
서버의 `MultiToolExecutor`가 결정한다. 모델이 임의로 Tool, URL, 학번 또는 실행
순서를 추가할 수 없다.

```text
검증된 ExecutionPlan
        ↓
의존 그래프를 실행 wave로 변환
        ↓
같은 wave: asyncio.gather로 병렬 실행
        ↓
다음 wave: 선행 결과 확인 후 순차 진행
        ↓
계획 순서대로 원본 Tool 결과 취합
```

예를 들어 성적과 시간표는 서로 독립적이므로 첫 wave에서 함께 실행한다. 학생
프로필의 전공을 확인한 뒤 규정을 검색하는 경우에는 프로필과 지식 검색을 서로
다른 wave로 배치한다.

## 인자 경계

기본 resolver는 모든 상황에서 안전한 필수 인자만 제공한다.

- 개인 학사 Tool: 인증 주체가 Registry에 이미 주입되므로 인자를 추측하지 않는다.
- 학교 지식 및 nDRIMS 검색: 원본 사용자 질문만 `question`으로 전달한다.
- 연도, 학기, 분류, 학번 같은 선택 인자는 임의로 생성하지 않는다.

의존 결과를 다음 Tool 인자로 변환해야 할 때는 `StepArgumentResolver`를 주입한다.
Resolver는 해당 단계가 명시적으로 의존한 결과만 전달받는다. 향후 Query Rewrite나
Context Builder가 이 경계를 구현할 수 있다.

## 실패 정책

- 각 단계의 기본 제한 시간은 15초다.
- 한 Tool의 timeout 또는 예외가 같은 wave의 다른 성공 결과를 지우지 않는다.
- 선행 결과가 `success` 또는 `partial`이면 후속 단계를 실행할 수 있다.
- 선행 결과가 없으면 후속 단계는 `blocked`로 기록하고 호출하지 않는다.
- 모든 단계 성공은 `success`, 일부만 사용 가능하면 `partial`, 사용 가능한 결과가
  하나도 없으면 `unavailable`이다.
- 내부 예외 문자열은 사용자용 결과에 포함하지 않는다.

Python 단계 timeout은 호출 결과를 기다리는 시간을 제한한다. 이미 worker thread에서
실행 중인 동기 I/O 자체를 강제로 종료할 수는 없으므로, 운영 전에는 HTTP client
timeout과 PostgreSQL `statement_timeout`도 함께 설정해야 한다.

이번 결과는 아직 응답용으로 줄이거나 개인정보를 제거하지 않은 원본 Tool
envelope다. 공통 응답 컨텍스트 변환과 token budget 적용은 Issue #26의 Context
Builder가 담당한다.
