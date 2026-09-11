# nDRIMS Menu Search Tool

`find_ndrims_menu`는 학생의 자연어 질문을 nDRIMS의 검증된 메뉴 경로와 연결한다. 동의어·약칭 목록을 코드에 두지 않고, 메뉴 제목과 breadcrumb를 Gemini 임베딩으로 색인하여 cosine similarity로 검색한다.

## 흐름

1. `seed_ndrims_menus`로 현재 학생 화면에서 확인한 메뉴 Registry를 갱신한다.
2. `index_ndrims_menus`가 `상위 메뉴 > 하위 메뉴` 텍스트의 임베딩을 한 번 저장한다.
3. Tool은 질문 임베딩과 활성 메뉴만 비교해 최대 5개의 후보를 반환한다.
4. 반환 Action은 `navigate_ndrims_menu`와 Registry의 `menu_key`만 사용한다. LLM이 URL이나 내부 메뉴 ID를 만들 수 없다.
5. Chrome 확장프로그램은 로그인된 탭에서 breadcrumb 또는 검증된 `external_menu_id`가 실제 보이는지 다시 확인한 후 이동한다.

## 실행

```powershell
python manage.py migrate
python manage.py seed_ndrims_menus
python manage.py index_ndrims_menus
```

`index_ndrims_menus`는 메뉴 경로 또는 임베딩 모델이 바뀐 항목만 다시 처리한다. `GEMINI_API_KEY`와 `GEMINI_EMBEDDING_MODEL`은 기존 공식 지식 RAG 설정을 그대로 사용한다.

## 현재 경계와 발전 항목

- 현재 Registry는 한 학생 계정에 실제 표시된 150개 메뉴 기준이다. 학적 상태·소속·권한별 메뉴 스냅샷을 추가 수집해야 한다.
- cosine 최소 점수 0.55는 대표 메뉴 질문(약 0.68~0.72)과 무관 질문(약 0.48)의 실측 결과로 정한 초기 안전 기준이다. 운영 전 더 큰 평가 데이터로 조정해야 한다.
- 확장프로그램 구현 전에는 후보 경로만 반환하며 실제 화면 이동을 완료했다고 표시하지 않는다.
- `external_menu_id`는 DOM에서 안정성과 권한별 일관성이 검증된 뒤에만 저장한다.
