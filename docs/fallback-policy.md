# Fallback, Partial, Clarification 정책

## 목적

Fallback Policy는 Tool·검색·문맥 부족이 있어도 Agent가 추측하거나 내부 오류를 노출하지
않도록 응답 경로를 서버에서 결정한다.

```text
Execution 결과 + ResponseContext
             ↓
Fallback Policy
  ├─ success              → Response Agent
  ├─ partial / truncated  → Response Agent + 서버 강제 limitation
  ├─ unavailable          → 서버 직접 안전 응답
  └─ clarification        → 서버 직접 재질문
```

## 상태별 정책

| 상태 | 사용자에게 보이는 처리 | Gemini 사용 |
|---|---|---|
| `success` | 검증된 사실·출처·Action으로 답변 | 사용 |
| `partial` | 확인된 사실은 답하고, 누락 범위를 명시 | 사용, limitation 강제 |
| `unavailable` | 필요한 정보를 확인하지 못했다는 안전한 안내와 재시도/공식 안내 제안 | 사용하지 않음 |
| `clarification` | Planner가 만든 한 가지 재질문 | 사용하지 않음 |
| `truncated=true` | 보이는 결과만 기준이라는 제한을 명시 | 사용, limitation 강제 |

`partial`에서는 실패한 Tool의 내부 메시지를 보여 주지 않는다. 대신 성공한 Capability와
실패한 Capability를 서버에서 분리하고, Response Agent에는 안전한 제한 설명만 전달한다.
Retry 가능한 실패이면 “잠시 후 다시 시도”를 추가한다.

## 최종 확정

Response Agent를 사용하는 경로에서도 Fallback Policy가 `required_limitations`를
초안에 병합한 뒤 Response Validator로 보낸다. 그러므로 모델이 제한 설명을 빼더라도
최종 `ValidatedResponse`에는 서버 정책이 남는다.

직접 fallback 응답은 Source·Action을 새로 만들지 않으며, 이미 검증된 Context 밖의
대체 URL을 제안하지 않는다.

