# Response Agent와 답변 초안

## 책임 경계

Response Agent는 `ResponseContext`의 검증된 사실을 한국어 답변으로 정리한다. 새로운
사실을 조회·계산·판정하거나 URL과 nDRIMS 메뉴를 생성하지 않는다.

```text
ResponseContext
  ├─ 개인 학사 사실
  ├─ 공식 근거와 source_id
  ├─ 검증된 Action과 action_id
  └─ partial / truncated / 오류 정보
               ↓
Google ADK Response Agent
               ↓
ResponseDraft
  answer + status + source_ids + action_ids + limitations
```

Gemini는 `ResponseDraft`만 생성한다. 후속 Issue #29의 Response Validator가 source ID,
Action ID, 상태와 사실 일치 여부를 검사한 뒤 UI가 사용할 최종 응답으로 확정한다.

## 답변 스타일

- 결론 또는 현재 상태를 첫 문장에 둔다.
- 기본 2~4문장, 500자 이내의 짧은 한국어 문단으로 작성한다.
- 개인 학사 사실은 현재 상태로, 공식 규정·일정은 공식 문서 기준으로 구분한다.
- 불확실·부분 실패·잘린 Context는 제한을 한 번만 자연스럽게 알린다.
- 출처 URL은 answer에 반복하지 않고 `source_ids`로 전달한다.
- 메뉴 이동은 `action_ids`로 전달하며, Agent는 이동을 실행하지 않는다.

예를 들어 졸업요건 정책 엔진이 아직 없는 현재 단계에서는 취득학점과 공식 총 기준을
함께 안내할 수 있지만, 전공·교양·필수과목이 모두 확인되지 않았다면 졸업 가능 여부를
단정하지 않는다.

## 입력 최소화

Response Agent 입력에는 Context Builder가 정리한 `items`, 오류·누락 상태, 인용 가능한
`source_id`·제목·쪽수, Action의 `action_id`·label만 들어간다. 원본 Tool envelope,
학번·표시 이름, 실행 ID, API 키, source URL, nDRIMS 세션 정보는 넣지 않는다.

## 현재와 후속 검증

Issue #28은 Agent·Schema·글쓰기 instruction을 구현한다. 모델 출력에 있는 ID가 실제
입력 allowlist에 존재하는지, 개인 사실이 Context를 벗어나지 않는지, partial 상태를
success로 바꾸지 않는지는 Issue #29에서 서버 Validator로 강제한다.

