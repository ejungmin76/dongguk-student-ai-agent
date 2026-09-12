# Response Validator

## 역할

Response Validator는 Gemini가 만든 `ResponseDraft`를 UI/API에 보내기 전에 서버에서
검사한다. 자연어를 더 잘 쓰게 하는 역할이 아니라, 모델이 Context 밖의 사실·출처·메뉴
이동을 만들어 내지 못하게 하는 경계다.

```text
ResponseDraft
  ├─ answer
  ├─ source_ids
  ├─ action_ids
  └─ status
          ↓
서버 Response Validator
          ↓
ValidatedResponse
  ├─ 서버 Context에서 다시 해석된 SourceReference
  └─ 서버 Context에서 다시 해석된 ActionReference
```

UI는 Gemini가 작성한 URL이나 Action 객체를 사용하지 않는다. Validator가 Context에
있던 ID를 실제 `SourceReference`·`ActionReference`로 바꾼 `ValidatedResponse`만
사용한다.

## 강제 규칙

- `status`는 `ResponseContext.status`와 정확히 같아야 한다.
- `partial`, `unavailable`, `truncated` Context에는 `limitations`가 반드시 있어야 한다.
- `source_id`는 Context의 출처 목록에 있어야 한다. 공식 문서 출처는 Pydantic이 검증한
  URL도 가져야 한다.
- `action_id`는 Context의 검증된 Action 목록에 있어야 한다.
- 답변·제한 설명·추가 질문에 등장하는 아라비아 숫자는 Context의 사실 항목에 있는
  숫자만 허용한다. 출처 쪽수나 Action ID 같은 메타데이터 숫자는 근거 사실로 취급하지
  않는다.
  따라서 취득 93학점과 기준 130학점은 말할 수 있지만, 코드 정책 평가 없이 계산한
  `37학점 부족`은 차단된다.

숫자 검사는 개인 학점·평점·날짜·금액처럼 고위험 사실을 위한 결정론적 1차 방어선이다.
자연어 전체 의미의 grounding은 다음 개선 대상이며, Response Agent에는 처음부터
Context 밖 사실을 쓰지 말라는 instruction이 적용되어 있다.

## 제한과 후속 개선

현재 검사는 한글로 풀어 쓴 수량이나 문장 의미 전체를 완전하게 증명하지 않는다. 이를
억지로 키워드 규칙으로 확장하지 않는다. 향후에는 사실 단위 evidence reference와 평가
데이터셋을 추가해, 모델 답변의 claim 단위 grounding을 강화한다. 이때도 LLM을 단독
심판으로 쓰지 않고 서버의 증거·정책 계약을 기준으로 한다.
