# 동국대 AI Assistant Chrome 확장프로그램

개발 중에는 별도 빌드 없이 이 폴더를 Chrome의 `chrome://extensions`에서 **압축해제된 확장 프로그램 로드**로 선택합니다.

1. Django API(`127.0.0.1:8000`)를 실행합니다.
2. Chrome에서 `chrome://extensions`를 열고 개발자 모드를 켭니다.
3. `extension` 폴더를 선택해 로드합니다.
4. 로그인된 `https://ndrims.dongguk.edu` 화면을 새로고침합니다.
5. 오른쪽 아래 ✦ 버튼을 눌러 챗봇을 엽니다.

확장프로그램은 자체 챗봇 화면을 사용하며 Django의 확장 전용 API만 호출합니다. 답변에 검증된 nDRIMS Action이 오면 확장프로그램이 경로의 마지막 메뉴를 현재 화면에서 찾아 클릭합니다. 메뉴 DOM이 바뀐 경우에는 경로만 안내하고 자동 클릭하지 않습니다.
