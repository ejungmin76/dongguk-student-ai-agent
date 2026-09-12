# Context Resolver와 Execution Planner

## 목적

Issue #23은 질문에 답하거나 Tool을 실행하지 않는다. Issue #22의 의미 분석을
실행 가능한 순서의 중간 표현(IR)으로 바꾸고, 서버 코드가 그 계획을 검증한다.

```text
QuestionAnalysis
        +
세션·시스템에 존재하는 Context 목록
        ↓
Context Resolver (결정론적 Python)
        ↓
resolved / deferred / missing
        ↓
Gemini Execution Planner
        ↓
ExecutionPlan JSON (Pydantic)
        ↓
Plan Validator (결정론적 Python)
```

## Context Resolver

Resolver는 값 자체를 Gemini에 공개하지 않고 어떤 필드가 준비됐는지만 구분한다.

- `resolved_fields`: 사용자 메시지, 인증 세션, 검증된 시스템 문맥에 이미 존재
- `deferred_fields`: 앞선 Capability 실행으로 얻을 수 있음
- `missing_fields`: Tool이나 현재 세션으로 해결할 수 없어 추가 질문 필요

예를 들어 전공과 입학연도는 인증된 `student_profile`로 얻을 수 있으므로
사용자에게 다시 묻지 않고 deferred로 분류한다.

## ExecutionPlan IR

각 단계는 다음만 포함한다.

- `step_id`: 계획 안에서만 쓰는 영문 식별자
- `capability`: 서버가 허용한 기능 enum
- `depends_on`: 먼저 성공해야 하는 단계
- `uses_context`: 단계가 읽는 문맥 필드
- `produces_context`: 이후 단계에 제공하는 문맥 필드

URL, SQL, Python 코드, 임의의 함수명이나 실제 학생 데이터는 계획에 들어가지
않는다. `steps`는 이미 위상 정렬된 순서여야 한다.

## 결정론적 검증

Gemini 출력은 실행 지시가 아니라 검증 대상 데이터다. Validator는 다음을 거부한다.

- 질문 분석에서 요청하지 않은 Capability
- 요청됐지만 누락된 Capability
- 존재하지 않거나 뒤에 있는 단계에 대한 의존
- 인증 문맥 없이 개인 학사 또는 nDRIMS Capability 사용
- Capability가 제공할 수 없는 Context를 제공한다고 주장하는 계획
- 의존 단계가 제공하지 않은 Context를 사용하는 계획
- 추가 질문과 실행 단계를 동시에 포함한 계획

따라서 모델이 잘못된 계획을 반환해도 후속 Executor까지 도달하지 않는다.

## 예시

`나 컴ㅁ에인데 우리 전공졸업학점 몇임?`은 다음 순서로 계획된다.

```text
profile: student_profile
  uses authenticated_student
  produces primary_major, admission_year

graduation_rules: university_knowledge
  depends_on profile
  uses primary_major, admission_year
```

`신청하고 싶어`처럼 대상이 불분명한 질문은 `steps=[]`와 하나의
`clarification_question`으로 끝난다. 이때 누락 문맥은 `target_service`로
표현하며 특정 신청 문구나 메뉴 이름을 코드에 등록하지 않는다.

실제 Capability→Tool 함수 연결과 실행은 후속 Tool Registry/Executor 이슈에서
구현한다.
