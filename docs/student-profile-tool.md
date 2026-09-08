# 학생 Profile 조회 Tool

`get_student_profile`은 로그인한 학생의 최소 학적 프로필만 반환하는 ADK 호환
Python 함수다. Google ADK Agent 생성 시 `tools` 목록에 등록할 수 있으며 실제 Agent
등록은 ADK 초기 구축 이슈에서 진행한다.

## 데이터 흐름

```text
Django 인증 -> AcademicToolActor -> StudentProfileTool
                                    -> AcademicRepository
                                    -> Pydantic ToolResult
```

`AcademicToolActor`는 Django 인증 계층이 생성한다. LLM 입력으로 생성하거나 요청
본문의 학번을 신뢰해서는 안 된다.

## 권한 정책

- 대상 학번을 생략하면 인증된 본인을 조회한다.
- 일반 학생이 다른 학번을 요청하면 `PROFILE_ACCESS_DENIED`를 반환한다.
- 인증 학번이 없으면 `AUTHENTICATION_REQUIRED`를 반환한다.
- Repository에 학생이 없으면 `STUDENT_NOT_FOUND`를 반환한다.
- 교직원과 관리자 권한은 실제 인증 요구사항이 정해진 후 추가한다.

## 최소 반환 필드

- 학번과 표시 이름
- 입학연도와 현재 학기
- 학적 상태와 일반/심화과정
- 주전공명과 선택적인 복수전공명

성적, 취득학점, 현재 수강, 시간표, 내부 DB ID는 반환하지 않는다. 각 데이터는 별도
Tool에서 필요한 권한을 다시 검사한 후 제공한다.

## ADK 등록 예시

```python
actor = AcademicToolActor(student_number=authenticated_student_number)
get_student_profile = build_get_student_profile_tool(actor)

root_agent = Agent(
    ...,
    tools=[get_student_profile],
)
```

인증 주체가 closure에 고정되므로 Agent가 Tool 인자로 인증 학번을 조작할 수 없다.
