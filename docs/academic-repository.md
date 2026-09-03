# Academic Repository

학사 Tool과 Service는 Django ORM을 직접 사용하지 않고 `AcademicRepository` 계약을
통해 학생 데이터를 조회한다. 현재 구현체는 `DjangoAcademicRepository` 하나뿐이다.

## 조회 계약

```python
repository.get_student_profile(student_number)
repository.list_academic_records(student_number)
repository.list_current_enrollments(student_number)
```

- 학생 기본정보, 전공, 교육과정, 시나리오 기준 학기를 조회한다.
- 과거 성적과 재수강 대체 여부를 조회한다.
- 현재 수강 강좌와 요일·시간·강의실을 조회한다.
- 존재하지 않는 학생은 `StudentNotFoundError`를 발생시킨다.
- 반환값은 Django model이나 QuerySet이 아닌 Pydantic DTO이다.

## 현재 사용

```python
from apps.academic.repositories import DjangoAcademicRepository

repository = DjangoAcademicRepository()
profile = repository.get_student_profile("MOCK-2026-008")
```

Repository는 조회에 필요한 `select_related`와 `prefetch_related`를 내부에서 적용한다.
호출자는 ORM 관계나 쿼리 최적화 방법을 알 필요가 없다.

## 학교 데이터로 교체할 때

학교 API 사용 가능 여부는 아직 확정하지 않는다. API, 읽기 전용 DB 또는 정기 CSV를
사용하게 되면 `AcademicRepository`와 같은 메서드를 제공하는 adapter를 추가한다.
Tool과 Service가 DTO만 사용하면 상위 코드는 변경하지 않는다.

이번 이슈에는 HTTP 요청, 학교 인증, 토큰, 가짜 API 구현체를 포함하지 않는다.
