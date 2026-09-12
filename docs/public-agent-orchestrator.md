# 공개형 Agent Orchestrator

공개 웹 배포의 한 요청은 다음 순서로 처리한다.

```text
질문 분석(Gemini) → 공개 Capability 경계 검사 → 실행 계획(Gemini)
→ 등록 Tool 실행 → 안전한 Context 축소 → 답변 작성(Gemini) → 서버 Validator
```

`university_knowledge`와 `ndrims_menu`만 Tool 실행 대상이다. 검색어는 원문을
그대로 사용하며, 익명 브라우저의 대화 기록·식별자·개인 학사값을 검색 문장에 넣지
않는다. 이 모드에서는 따라서 Query Rewrite가 의미를 보태지 않는 identity rewrite다.

## 개인 정보 경계

질문 분석 결과에 `student_profile`, `academic_records`, `current_schedule` 중 하나라도
포함되면 계획·Tool 실행·Gemini 답변 작성을 진행하지 않는다. 대신 사용자가 직접
nDRIMS에 로그인하도록, 서버 상수로 검증된 공식 주소만 `open_url` Action으로 반환한다.

nDRIMS 메뉴 검색은 메뉴명·breadcrumb·공식 도메인 주소만 담긴 서버 레지스트리를
검색한다. AI는 비밀번호, 쿠키, 로그인 상태, 화면의 개인 데이터를 받거나 저장하지
않으며 URL을 생성할 수도 없다.

## 실패 처리

공식 자료 검색 또는 모델 호출에 실패하면 내부 예외를 노출하지 않고 `unavailable`
상태로 응답한다. 결과가 일부뿐이면 Fallback 정책이 제한 사항을 답변에 붙이고,
최종 Validator는 Context에 존재하는 source/action ID 및 숫자 사실만 통과시킨다.
