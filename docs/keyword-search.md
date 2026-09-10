# PostgreSQL FTS와 메타데이터 검색

## 키워드 기준

고정된 키워드 사전을 쓰지 않는다. 질문을 유니코드 정규화하고 `컴퓨터·AI학부`처럼 중간점으로 연결된 표현을 나눈 뒤, 한글·영문·숫자로 된 두 글자 이상 토큰을 검색어로 사용한다. `알려줘`, `어떻게`처럼 검색 의미가 거의 없는 표현만 제외한다.

문서 제목, 섹션 경로, 분류, 적용 연도, 본문을 하나의 PostgreSQL `simple` FTS 벡터로 만든다. `simple` 설정은 한국어 형태소 분석을 주장하지 않고 정확한 용어 매칭에 집중한다. 의미·조사 변형 탐색은 #17 Dense 검색이 담당한다.

## 필터

- `--effective-year 2026`: 적용 연도 일치
- `--document-status active`: 활성/보관/미확인 문서 상태
- `--effective-on 2026-09-01`: 시작일 이전 및 종료일 이후가 아닌 문서
- `--category graduation`: 출처 카탈로그 분류

현재 수집 카탈로그에 시행 시작·종료일이 없는 자료는 기간 필터에서 미확인(`null`)으로 남긴다. 날짜를 추측하지 않는다.

## 실행

마이그레이션 후 기존 청크의 FTS 벡터를 한 번 만든다.

```powershell
python manage.py migrate
python manage.py rebuild_university_fts
```

정확한 용어 검색:

```powershell
python manage.py search_university_knowledge_fts "재수강 C+"
```

연도·분류를 함께 제한:

```powershell
python manage.py search_university_knowledge_fts "졸업" --effective-year 2026 --category graduation
```
