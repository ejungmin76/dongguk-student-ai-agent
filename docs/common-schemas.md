# Common Tool and Agent schemas

Tool과 Agent가 주고받는 공통 envelope는 `ToolResult[T]`를 사용한다. `T`는 각 Tool 구현 이슈에서 정의하는 Pydantic 모델이며 검증되지 않은 `dict[str, Any]`를 정식 계약으로 사용하지 않는다.

## 공통 구조

```json
{
  "status": "success",
  "data": {},
  "sources": [],
  "actions": [],
  "errors": [],
  "meta": {
    "tool_name": "get_academic_records",
    "execution_id": "exec_123",
    "duration_ms": null
  }
}
```

## 상태 규칙

| 상태 | data | errors | 의미 |
|---|---|---|---|
| `success` | 필수 | 비어 있음 | 요청을 모두 처리함 |
| `partial` | 필수 | 1개 이상 | 일부 결과와 실패 원인을 함께 반환함 |
| `clarification` | 선택 | 1개 이상 | 입력이 부족하거나 모호함 |
| `unavailable` | 없음 | 1개 이상 | 필요한 데이터나 시스템을 사용할 수 없음 |

## 공통 모델

- `ErrorDetail`: 안정적인 대문자 오류 코드, 안전한 메시지, 재시도 가능 여부
- `SourceReference`: 학사 DB, 공식 문서, 서비스 Registry 등의 추적 가능한 근거
- `ActionReference`: 서버에 등록된 Action ID와 검증 가능한 HTTP(S) URL
- `ResultMeta`: Tool 이름, 실행 ID, 선택적인 실행 시간

`SourceReference`에는 학생의 실제 성적이나 개인정보를 복제하지 않는다. `ActionReference.url`은 Schema가 HTTP(S) 형식만 검사하며, 실제 학교 도메인과 권한 검사는 University Service에서 수행한다.

## Tool별 data 모델

이번 공통 Schema에서는 Tool별 `data` 필드를 확정하지 않는다. 각 Tool은 구현 시 전용 모델을 정의한다.

```python
class AcademicRecordData(BaseModel):
    cumulative_gpa: Decimal
    completed_credits: int


result = ToolResult[AcademicRecordData](...)
```

## 직렬화와 복원

```python
payload = result.model_dump_json()
restored = ToolResult[AcademicRecordData].model_validate_json(payload)
```

알 수 없는 필드는 허용하지 않으며 상태와 `data/errors` 조합이 모순되면 Pydantic `ValidationError`를 발생시킨다.
