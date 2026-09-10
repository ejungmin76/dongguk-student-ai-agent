# RAG 문서 청크화

## 목적

정제된 `data/knowledge/cleaned/*.md`를 제목·소제목 기준의 검색 단위로 나눈다. 원문 전체를 LLM에 전달하지 않고, 질문과 관련된 청크만 다음 임베딩·검색 단계에 전달하기 위한 준비 과정이다.

## 실행

공개 문서를 수집·정제한 뒤 실행한다.

```powershell
python manage.py chunk_university_knowledge
```

결과는 Git에서 제외되는 `data/knowledge/chunks/chunks.jsonl`에 생성된다. 한 줄이 하나의 청크이며, 이후 pgvector 저장 단계의 입력으로 사용한다.

## 청크 계약

각 청크는 Pydantic으로 검증되며 다음 정보를 보존한다.

- `source_id`, `document_title`, `canonical_url`, `source_type`, `category`: 출처와 검색 필터 정보
- `effective_year`, `fetched_at`, `content_hash`: 적용 시점과 갱신 판단 정보
- `heading_path`: 예: `수강신청 > 신청 가능 학점`
- `page_start`, `page_end`: PDF에 `<!-- page: N -->` 표식이 있으면 원문 페이지를 기록한다. 기존 정제 문서에 표식이 없으면 `null`이며 문서 전체 페이지 수는 수집 manifest에 남는다.
- `content`: 실제 검색·임베딩 대상 본문

## 분할 기준과 실험

기본값은 최대 **1,200자**, 이전 청크의 문맥 **150자 overlap**이다. 한국어 공지·가이드에서 세부 정책을 유지하면서도 검색 결과가 지나치게 넓어지지 않는 시작값이다. 짧은 섹션도 독립적인 정책일 수 있어 삭제하지 않는다.

- 제목이 바뀌면 청크를 섞지 않는다.
- 긴 섹션만 문단 경계로 여러 청크로 나누고 다음 청크 앞에 직전 청크 마지막 문맥을 넣는다.
- 표와 목록은 문단 블록으로 취급해 가능한 한 분리하지 않는다.

아래처럼 값은 실험할 수 있다.

```powershell
python manage.py chunk_university_knowledge --max-chars 1000 --overlap-chars 120
```

다음 검색 이슈에서는 대표 질문(수강 가능 학점, 재수강, 졸업요건, 장학 신청)을 대상으로, 상위 검색 결과가 적절한 제목과 출처를 유지하는지 비교한다.
