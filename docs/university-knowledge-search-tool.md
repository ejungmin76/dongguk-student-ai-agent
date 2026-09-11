# `search_university_knowledge` Tool

## 역할

공식 동국대학교 공개 자료에서 질문의 근거 청크와 인용 가능한 출처를 검색한다. 답변을 생성하거나 학교 메뉴로 이동시키지 않는다.

```text
학생 질문 또는 Planner 검색 질의
        ↓
Hybrid RRF (Dense + PostgreSQL FTS)
        ↓
ToolResult: 근거 청크 + 중복 제거한 공식 출처
```

## 입력

| 필드 | 설명 |
|---|---|
| `question` | 학생의 원문 질문 또는 Planner가 만든 검색 질의 |
| `effective_year` | 학생 프로필에서 확인된 적용 교육과정·문서 연도(선택) |
| `effective_on` | 질문이 특정 시점의 규정을 묻는 경우의 기준일(선택) |
| `top_k` | 반환할 근거 청크 수, 기본·최대 5개 |

서비스 분류나 메뉴 이름은 입력으로 받지 않는다. `find_university_service` Tool은 #35에서 별도로 구현한다.

## 반환 원칙

- `success`: 근거 청크와 공식 URL·문서명·제목 경로·적용 정보 반환
- `unavailable`: 검색 결과가 없거나 검색 인프라를 사용할 수 없음
- 한 문서에서 여러 청크가 나오더라도 `sources`에는 문서당 한 번만 반환
- PDF 페이지 정보가 수집된 청크만 페이지를 반환하며, 없는 페이지는 추측하지 않음
- Agent는 이 Tool의 내용만으로 확정 답변을 만들지 않고, 다음 단계에서 출처와 적용 조건을 함께 검증해야 함

## ADK 연결 시점

`build_search_university_knowledge_tool()`은 JSON을 반환하는 ADK 호환 함수다. 실제 Google ADK의 Tool 등록과 선택은 #24에서 처리한다.
