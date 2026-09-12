# 동국대 AI Assistant Chrome 확장프로그램

개발 중에는 별도 빌드 없이 이 폴더를 Chrome의 `chrome://extensions`에서 **압축해제된 확장 프로그램 로드**로 선택합니다.

1. Django API(`127.0.0.1:8000`)와 Next 개발 서버(`localhost:3000`)를 실행합니다.
2. Chrome에서 `chrome://extensions`를 열고 개발자 모드를 켭니다.
3. `extension` 폴더를 선택해 로드합니다.
4. 로그인된 `https://ndrims.dongguk.edu` 화면을 새로고침합니다.
5. 오른쪽 아래 ✦ 버튼을 눌러 챗봇을 엽니다.

확장프로그램 전용 페이지가 로컬 챗봇을 불러오므로 nDRIMS의 로컬 네트워크 차단을 피합니다. 현재는 UI 삽입과 API 연결을 먼저 제공합니다. nDRIMS 내부 메뉴를 실제로 클릭하는 동작은 메뉴 Action 검증 단계에서 추가합니다.
