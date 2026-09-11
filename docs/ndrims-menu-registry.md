# nDRIMS Menu Registry

## 범위

이 Registry는 학생이 직접 로그인한 nDRIMS 안에서 메뉴를 찾고 이동시키는 Chrome 확장프로그램을 위한 서버 측 메뉴 지도다. 다른 학교 시스템의 서비스 목록이나 학생 개인정보를 저장하지 않는다.

## 데이터 구조

`NdrimsMenu` 하나로 계층과 이동 단서를 관리한다.

- `menu_key`: 우리 서버가 쓰는 안정적인 식별자
- `title`, `parent`, `sort_order`: 실제 메뉴명과 계층 경로
- `external_menu_id`: nDRIMS 화면에서 장차 확인하는 내부 메뉴 식별자. 확인 전에는 비운다.
- `source_url`, `verified_at`: nDRIMS 공식 화면을 마지막으로 확인한 근거
- `is_active`: 메뉴가 폐기되었거나 숨겨진 경우 비활성화하는 상태

각 메뉴는 nDRIMS 공식 도메인만 출처로 허용한다. 메뉴마다 별도 Action 또는 외부 URL을 만들지 않는다. 확장프로그램은 로그인된 nDRIMS 탭에서 Registry의 breadcrumb 또는 확인된 `external_menu_id`를 이용해 이동한다.

## 보안 경계

- 서버는 nDRIMS 비밀번호, 쿠키, 화면의 개인 학사정보를 받거나 저장하지 않는다.
- 메뉴가 현재 학생에게 실제로 노출되는지는 확장프로그램이 로그인 세션 안에서 확인한다.
- 신청·제출·수정은 학생이 nDRIMS 화면에서 직접 수행한다.

## Seed

`apps/ndrims/seed_data/student_menus.yaml`은 2026-09-11에 로그인된 학생 화면에서 직접 확인한 메뉴 트리다. 현재 학생 화면에서 보인 최상위·하위 메뉴 **150개**를 담는다. 메뉴명이 보였다는 사실만 저장하며, 개인 식별정보나 화면 내용은 저장하지 않는다. 다른 권한·학적 상태에서만 보이는 메뉴는 이후 별도 검증으로 추가한다.

```powershell
python manage.py migrate
python manage.py seed_ndrims_menus
```

명령은 여러 번 실행해도 같은 `menu_key`를 갱신하므로 중복 메뉴를 만들지 않는다.
