# 공개 학사 지식 수집 파이프라인

## 목적

[`university-knowledge-sources.yaml`](./university-knowledge-sources.yaml)의 공식 공개 HTML/PDF를 원본 보존, 텍스트 추출, 정제, 출처 기록까지 일관되게 처리한다. 이 결과는 다음 이슈에서 청크와 임베딩의 입력으로 사용한다.

## 실행

가상환경을 활성화한 뒤 의존성을 설치한다.

```powershell
python -m pip install -r requirements\development.txt
python manage.py ingest_university_knowledge
```

대표 소스 한 개만 시험하려면 다음과 같이 실행한다.

```powershell
python manage.py ingest_university_knowledge --source dgu-computer-ai-curriculum-2026 --interval 0
```

`enabled: false` 소스까지 명시적으로 처리하려면 `--all`을 사용한다. 다만 로그인 화면으로 연결되는 소스는 공개 RAG 수집 대상이 아니므로 활성화하지 않는다.

## 출력

실행 결과는 모두 `data/knowledge/`에 저장되며 Git에서 제외된다.

```text
data/knowledge/
├── raw/        # 서버 응답 원본 HTML/PDF
├── parsed/     # 추출한 제목·본문 JSON
├── cleaned/    # 검색용 Markdown + 출처 front matter
└── manifests/  # URL, 해시, 수집시각, 파일 위치, 처리 상태
```

## 정제 규칙

- HTML: `nav`, `header`, `footer`, `script`, `style` 등 사이트 레이아웃을 제거하고 제목·문단·목록·표를 Markdown으로 보존한다.
- PDF: 한국어 CMap 복원 품질이 높은 PyMuPDF로 페이지별 텍스트를 추출하고, 실패하면 pypdf로 한 번 더 시도한 뒤 다수 페이지의 상단·하단에 반복되는 머리말·바닥글을 제거한다.
- 한국어 원문, 목록, 표의 행·열은 평탄한 한 줄 텍스트로 바꾸지 않는다.
- 인접한 중복 문장만 제거한다. 서로 다른 문단의 우연한 동일 문장은 삭제하지 않는다.
- 이미지로만 된 PDF 표는 텍스트 추출 결과가 비어 있을 수 있으므로, 이후 OCR과 사람 검증이 필요한 대상으로 기록한다.

## 운영 경계

- YAML에 등록된 공개 URL만 요청한다.
- 로그인, 쿠키, nDRIMS/e-Class 개인 화면, 학생별 데이터는 처리하지 않는다.
- 기본 요청 간격은 3초이며 소스는 순차 처리한다.
- 문서가 변경되면 SHA-256과 수집시각이 manifest에 남는다.
