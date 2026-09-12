# 웹·Chrome 확장 역할 경계

## 공통

Django Agent API는 공식 지식 검색, 출처 반환, 검증된 nDRIMS 메뉴 경로 검색을 공통으로 제공한다. 웹과 확장은 같은 `answer`, `source`, `action` 이벤트 계약을 사용한다.

## 웹

웹은 로그인 없는 공식 안내 채널이다. 답변, 출처, nDRIMS 메뉴 경로와 nDRIMS 메인 링크만 표시한다. nDRIMS 내부 메뉴 실행, 세션 접근, 개인 학사정보 처리는 하지 않는다.

## Chrome 확장

확장은 로그인된 nDRIMS 탭 안에서 같은 안내를 제공한다. `navigate_ndrims_menu` Action은 사용자가 누른 경우에만 현재 화면에서 검증된 메뉴 행을 찾아 연다. 비밀번호, 쿠키, 개인 학사정보를 Django API로 전송하거나 저장하지 않는다.
