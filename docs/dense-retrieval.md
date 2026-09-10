# Dense Vector Retrieval

## 역할

학생 질문을 `gemini-embedding-2`의 768차원 벡터로 바꾼 뒤, pgvector의 cosine distance로 가장 가까운 공식 문서 청크를 찾는다. 기본 후보 수는 **Top 5**이며 다음 Hybrid/Reranker 단계가 이 후보를 더 정교하게 다룬다.

## 실행

```powershell
python manage.py search_university_knowledge "이번 학기 최대 몇 학점까지 신청할 수 있어?"
```

후보 수를 조정할 수 있다.

```powershell
python manage.py search_university_knowledge "재수강 조건 알려줘" --top-k 3
```

결과에는 점수(`score`), 문서명, 제목 경로, 원문 페이지(알 수 있는 경우), 공식 URL, 본문이 JSON으로 반환된다.

## Gemini 형식

문서에는 `title: {title}`와 `text: {content}` 구조를 사용하고, 세부 정책 문맥인 제목 경로도 함께 전달한다. 질문에는 `task: question answering | query: {question}` 구조를 사용한다. 이는 Gemini Embedding 2의 비대칭 검색 권장 형식이며, 질문과 근거 문서가 같은 벡터 공간에서 비교되도록 한다.

## 검증 기준

- 임베딩이 없는 청크는 검색하지 않는다.
- cosine distance가 작은 순서로 반환하고, API 응답에는 사람이 해석하기 쉬운 `score = 1 - distance`를 제공한다.
- 기본값은 Top 5, 허용 범위는 1~20이다.
- 대표 질문의 상위 결과가 수강신청·재수강·졸업요건 등 해당 정책 섹션과 공식 URL을 반환하는지 확인한다.
