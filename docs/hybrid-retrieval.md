# Hybrid Retrieval (RRF)

## 목적

의미 검색(Dense)과 정확 용어 검색(FTS)의 점수 단위는 서로 다르므로 점수를 직접 더하지 않는다. 각 결과의 순위만 사용해 Reciprocal Rank Fusion(RRF)으로 결합한다.

```text
RRF 점수 = Σ 1 / (60 + 각 검색의 순위)
```

두 검색 방식에서 모두 상위권인 공식 청크가 우선한다. 같은 점수면 `chunk_id` 순서로 결정하므로 결과가 재현 가능하다. Gemini Reranker 호출은 하지 않는다.

## 처리 순서

1. 전공·입학연도·문서 상태·시점·분류 필터를 Dense와 FTS에 먼저 동일하게 적용한다.
2. Dense 10개와 FTS 10개를 각각 후보로 가져온다.
3. 청크별 RRF 점수를 합산해 최종 상위 5개를 반환한다.
4. 응답에는 각 청크의 Dense/FTS 순위, 공식 URL, 적용연도와 문서 상태를 포함한다.

오타 검색은 독립적인 후보 탐색 도구로 유지한다. 평가에서 필요성이 확인되기 전에는 Hybrid 기본 순위에 섞지 않는다.

## 실행

```powershell
python manage.py search_university_knowledge_hybrid "이번 학기 최대 몇 학점까지 신청할 수 있어?"
```

필터를 결합하는 예시:

```powershell
python manage.py search_university_knowledge_hybrid "졸업 학점" --effective-year 2026 --document-status active --category graduation
```

## 품질·지연 기준선

검증 질문마다 Dense 단독 결과와 Hybrid 결과의 상위 5개를 비교한다. 핵심 지표는 `Recall@5`(정답 공식 근거가 상위 5개에 포함되는 비율)와 검색 단계 지연 시간이다. RRF가 Dense보다 일관되게 낮은 결과를 보이거나, 정답 근거가 상위 5개에 반복해서 빠질 때만 가중 RRF·한국어 분석기·전용 Reranker를 평가한다.
