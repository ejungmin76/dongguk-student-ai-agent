# Response Context Builder

## 역할

Context Builder는 Gemini 프롬프트가 아니다. Multi-Tool Executor가 모은 원본
`ToolResult` envelope를 Response Agent에 전달할 최소·일관된 데이터 계약으로
변환하는 서버 계층이다.

```text
원본 Tool output
  data + sources + actions + errors + meta
                    ↓
Capability별 안전한 projection
                    ↓
중복 출처·Action 제거, 개인정보·실행 메타데이터 제거
                    ↓
token budget 안의 ResponseContext
```

## 보존·제거 규칙

| 결과 | 유지 | 제거 |
|---|---|---|
| 학생 Profile | 전공, 입학연도, 학기, 상태 | 학번, 표시 이름 |
| 성적·이수 | 평점·학점 요약, 학기/영역 요약, 과목 이력 | 학번 |
| 현재 시간표 | 학기, 과목, 시간, 강의실, 충돌 | 학번 |
| 공식 문서 검색 | 근거 문장, 제목 경로, 시행 정보, `source_id` | 검색 점수·rank·처리 시간·중복 URL |
| nDRIMS 메뉴 | 메뉴 후보, breadcrumb, 선택 필요 여부, 검증된 Action | 검색 점수·원본 URL |

`sources`와 `actions`는 Tool 결과의 Pydantic 계약을 다시 검증한 뒤 중복 제거한다.
이는 Response Agent가 공식 문서 인용과 검증된 nDRIMS 이동 Action을 잃지 않도록
한다.

## Token budget

기본 예산은 2,500 tokens다. 현재는 외부 provider tokenizer를 설치하지 않았으므로
직렬화된 JSON 2문자당 1 token이라는 보수적 추정치를 사용한다. 실제 Gemini tokenizer를
도입하면 이 추정기만 교체하면 된다.

예산을 넘으면 가장 큰 목록의 뒤쪽 항목부터 제거하고, `truncated=true` 및
`omissions`에 제거 경로와 개수를 기록한다. 즉, Response Agent는 결과가 완전하지
않음을 알 수 있으며 누락된 사실을 만들어 답하면 안 된다. 기본적으로 검색 결과는
이미 rank 순서이고, 나머지 목록은 Tool이 반환한 원래 순서를 보존한다.

Context Builder는 사실을 요약하거나 답변을 만들지 않는다. 자연어 답변과 인용 표기는
후속 Response Agent 이슈의 책임이다.

