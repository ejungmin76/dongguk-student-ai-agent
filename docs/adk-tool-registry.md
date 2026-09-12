# ADK Tool Registry와 단일 Tool 호출

## 목적

Issue #24는 검증된 `Capability`를 실제 Python 함수에 연결한다. Gemini는 Registry를
수정하거나 임의의 함수명, URL, SQL을 실행할 수 없다.

```text
검증된 단일 단계 ExecutionPlan
        ↓
서버 Tool Registry
        ↓
인증 및 Capability 확인
        ↓
선택된 FunctionTool 하나만 ADK Agent에 노출
        ↓
Gemini Function Calling
        ↓
기존 ToolResult JSON
```

## Registry 매핑

| Capability | ADK FunctionTool | 인증 필요 |
|---|---|---:|
| `student_profile` | `get_student_profile` | 예 |
| `academic_records` | `get_academic_records` | 예 |
| `current_schedule` | `get_current_schedule` | 예 |
| `university_knowledge` | `search_university_knowledge` | 아니요 |
| `ndrims_menu` | `find_ndrims_menu` | 예 |
| `general_response` | 없음 | 아니요 |

`general_response`는 외부 데이터를 조회하는 Tool이 아니므로 FunctionTool을 만들지
않는다.

## 보안 경계

- Registry 정의와 인증 주체는 서버 코드가 제공한다.
- 개인 학사 및 nDRIMS 기능은 인증 학생이 없으면 ADK에 노출되기 전에 거부된다.
- 계획에서 선택하지 않은 Tool은 Agent의 `tools` 목록에 들어가지 않는다.
- Tool 내부에서도 본인 조회 여부와 Pydantic 입력을 다시 검증한다.
- nDRIMS Tool은 메뉴 후보와 검증 대상 Action만 반환하며 신청을 실행하지 않는다.
- 실제 학생 데이터, API 키, 쿠키, nDRIMS 세션은 프롬프트나 Registry에 저장하지 않는다.

## 입력 Schema

ADK의 `FunctionTool`은 기존 Python 함수의 타입 힌트와 docstring으로 Gemini에
전달할 함수 선언을 생성한다. 검색 질문 외의 연도·학기·분류 등 선택 인자는
사용자 또는 앞 단계 결과로 확인되지 않으면 생략하도록 instruction에 명시한다.

ADK 실행 루프는 비동기이지만 기존 Django ORM Repository는 동기 API다. Registry의
명시적 타입 어댑터가 `sync_to_async(thread_sensitive=True)`로 호출 경계를 변환한다.
따라서 Django의 비동기 안전 검사를 끄지 않으면서 기존 트랜잭션과 DB 연결 규칙을
유지한다.

## 현재 범위

이번 이슈는 실행 단계가 하나인 계획만 호출한다. 두 개 이상의 Tool을 순차 또는
병렬로 실행하고 앞 단계 결과를 다음 단계 인자로 바인딩하는 기능은 후속
Multi-Tool Executor 이슈에서 구현한다.
