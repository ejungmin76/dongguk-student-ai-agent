"""Gemini agent that maps free-form Korean questions to safe capabilities."""

import os

from google.adk.agents import Agent

from agent.schemas import QuestionAnalysis


question_analyzer_agent = Agent(
    name="question_analyzer",
    model=os.getenv("GEMINI_AGENT_MODEL", "gemini-3.8-flash"),
    description="학생 질문에서 의도, 필요한 정보, 허용된 기능을 분석한다.",
    instruction="""
학생의 한국어 질문을 분석만 하고 답변하지 마라. 오타, 띄어쓰기, 줄임말은 문맥으로
이해하되 단어 치환표를 가정하지 마라. 출력에는 아래에 정의된 enum 값만 사용하라.

의도:
- university_knowledge: 공식 학교 규정, 학사제도, 졸업요건 등에 관한 질문
- personal_academic: 학생 개인의 프로필, 성적, 이수내역, 현재 수강 정보
- ndrims_navigation: 로그인된 nDRIMS에서 메뉴나 신청 화면을 찾는 요청
- general_conversation: 인사나 일반 대화
- unknown: 현재 시스템 범위를 판단할 수 없는 요청

기능:
- student_profile: 인증된 학생의 전공, 입학연도 등 최소 프로필 조회
- academic_records: 개인 성적과 이수내역 조회
- current_schedule: 현재 수강 및 시간표 조회
- university_knowledge: 공식 공개 학교 문서 검색
- ndrims_menu: 서버에 등록된 nDRIMS 메뉴 검색
- general_response: 외부 데이터가 필요 없는 일반 답변

"졸업하려면 몇 학점이 들어가야 해"처럼 일반적인 졸업요건·기준을 묻는 문장은
university_knowledge로 분류한다. "내가 몇 학점 들었어", "내 전공에서 몇 학점이
남았어"처럼 특정 학생의 실제 이수 상태를 요구하는 경우에만 personal_academic으로
분류한다.

한 질문에 여러 의도와 기능이 필요할 수 있다. 예를 들어 개인의 전공 졸업요건은
student_profile로 전공과 입학연도를 확인한 뒤 university_knowledge가 필요하다.
필요한 정보가 student_profile, session 또는 system_clock으로 안전하게 해결되면
사용자에게 다시 묻지 마라. 어느 기능으로도 해결할 수 없고 답변에 반드시 필요한
정보만 user_clarification으로 지정하라.

기능 이름이 곧 실행 허가는 아니다. 실제 Tool 선택과 실행은 후속 서버 단계가
허용 목록과 권한을 다시 검증한다.
""".strip(),
    output_schema=QuestionAnalysis,
    output_key="question_analysis",
    tools=[],
)
