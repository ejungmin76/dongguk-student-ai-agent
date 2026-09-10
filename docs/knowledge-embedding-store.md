# pgvector 임베딩 저장소

## 목적

청크화된 공식 문서를 PostgreSQL에 저장하고, Gemini가 만든 768차원 임베딩을 pgvector에 함께 보관한다. 다음 검색 단계는 질문도 같은 모델로 임베딩한 뒤 코사인 거리로 가까운 청크를 찾는다.

## 구조

`KnowledgeDocument`는 공식 자료 하나의 최신 출처·시점·해시를, `KnowledgeChunk`는 그 자료의 제목 경로·본문·페이지와 임베딩을 저장한다.

- `KnowledgeDocument.source_id`는 공식 자료의 안정적인 식별자다.
- `KnowledgeChunk.chunk_id`는 청크화 단계가 만든 안정적인 식별자다.
- `embedding`은 `vector(768)`이며 cosine distance용 HNSW 인덱스가 생성된다.
- 같은 `chunk_id`와 같은 본문 해시를 다시 적재하면 Gemini 호출과 DB 갱신을 건너뛴다. 본문이 바뀐 청크만 다시 임베딩한다.
- 같은 문서를 새 청크 설정으로 다시 처리하면, 현재 결과에 없는 이전 청크와 벡터는 자동으로 제거한다.

## 준비

Google AI Studio에서 발급한 Gemini API 키를 로컬 `.env`에만 추가한다. 실제 키를 Git에 올리지 않는다.

```text
GEMINI_API_KEY=실제_키
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
```

의존성과 마이그레이션을 적용한다.

```powershell
python -m pip install -r requirements\development.txt
python manage.py migrate
```

## 실행

먼저 `chunks.jsonl`이 있어야 한다.

```powershell
python manage.py index_university_knowledge
```

API 호출 없이 문서·청크 테이블과 중복 방지만 확인하려면 다음을 사용한다.

```powershell
python manage.py index_university_knowledge --skip-embeddings
```

## 모델 선택

`gemini-embedding-2`와 768차원을 사용한다. Google의 현재 Gemini 임베딩 문서는 768·1536·3072 차원을 권장하며, 768은 이 PoC의 약 1천 개 청크에 필요한 저장공간·검색 속도와 의미 검색 품질의 균형점이다. 문서 임베딩에는 문서 제목과 제목 경로를 본문과 함께 전달한다. 질문 임베딩도 다음 검색 이슈에서 동일 모델·호환되는 retrieval 형식으로 생성해야 한다.

## 운영 경계

- 공개 학교 문서와 생성된 청크만 Gemini에 전달한다. 학생 개인정보·nDRIMS 로그인 정보는 전달하지 않는다.
- 임베딩 벡터와 DB 내용은 로컬 PostgreSQL에 남고, `data/knowledge/` 원본·청크 파일은 Git에 올라가지 않는다.
- 임베딩 모델 또는 차원을 바꾸면 기존 벡터와 섞으면 안 되므로, 새 차원의 DB 컬럼/마이그레이션과 전체 재임베딩을 별도 변경으로 진행한다.
