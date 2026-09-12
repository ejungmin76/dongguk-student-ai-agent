# 질문 의도·필요 정보·기능 계약

## 목적

학생의 자유로운 한국어 질문을 코드에 등록된 문장이나 동의어와 대조하지 않고,
Gemini가 의미 수준에서 해석하도록 한다. 해석 결과는 서버가 허용하는 안정적인
기능 경계로만 표현한다.

```text
자연어 질문과 오타
        ↓
Gemini Question Analyzer
        ↓
QuestionAnalysis (Pydantic 검증)
        ↓
후속 Planner의 Tool 허용 목록·권한 검증
```

## 상위 의도

- `university_knowledge`: 공식 학교 규정과 학사제도
- `personal_academic`: 개인 프로필·성적·수강 정보
- `ndrims_navigation`: 로그인된 nDRIMS 메뉴 탐색
- `general_conversation`: 외부 데이터가 필요 없는 대화
- `unknown`: 현재 기능 범위를 판단할 수 없음

한 질문은 둘 이상의 의도를 가질 수 있다. 의도는 문구별 라우팅 규칙이 아니라
보안과 데이터 접근 경계를 나누는 값이다.

## 허용 기능

- `student_profile`
- `academic_records`
- `current_schedule`
- `university_knowledge`
- `ndrims_menu`
- `general_response`

Gemini는 위 기능 중 필요한 것을 요청할 수 있지만 Tool 이름, URL 또는 임의의
기능을 만들 수 없다. 실제 Tool 등록·선택 단계가 기능을 Tool로 매핑하고 사용자
권한을 검증한다.

## 필요한 문맥

`ContextNeed`는 답변 조건과 그 값을 얻을 안전한 출처를 함께 기록한다. 전공과
입학연도를 `student_profile`로 조회할 수 있다면 사용자에게 다시 묻지 않는다.
Tool이나 세션으로 해결할 수 없는 필수 정보만 `user_clarification`으로 지정한다.

예시:

```json
{
  "intents": ["university_knowledge"],
  "capabilities": ["student_profile", "university_knowledge"],
  "context_needs": [
    {
      "field": "primary_major",
      "source": "student_profile",
      "reason": "전공별 졸업요건 검색에 필요"
    },
    {
      "field": "admission_year",
      "source": "student_profile",
      "reason": "입학연도별 적용 기준 확인에 필요"
    }
  ],
  "needs_clarification": false,
  "clarification_question": null,
  "rationale": "개인 전공 기준의 공식 졸업요건 질문"
}
```

## 하드코딩 경계

코드에 사용자 문장, 오타, 약칭, 동의어 표를 저장하지 않는다. 코드로 제한하는
값은 실제 제공 기능과 인증·데이터 경계뿐이다. 이 목록이 변경되면 Tool Registry와
함께 명시적으로 검토한다.

## 검증

```powershell
python manage.py test tests.test_question_analysis --settings=config.settings.test
python manage.py test --settings=config.settings.test
```
