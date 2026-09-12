# Agent Chat API

`POST /api/chat/` is the authenticated web UI boundary. It accepts only JSON:

```json
{"message": "최대 학점이 몇 학점이야?", "session_id": null}
```

`session_id` is optional for a first message. The response always includes it,
plus `status`, `answer`, `sources`, `actions`, `limitations`, and an optional
`follow_up_question`. The UI must retain only this opaque UUID; it must not
choose a student identity.

For every request, Django derives the authenticated subject from its login
session, checks the conversation owner and expiry, stores a bounded user turn,
then passes the same UUID to the ADK runtime. A successful structured response
is stored as a bounded assistant turn. The API returns no internal tool,
provider, or exception details.

| Code | HTTP | Meaning |
| --- | --- | --- |
| `AUTHENTICATION_REQUIRED` | 401 | Login required |
| `INVALID_REQUEST` | 400 | Invalid JSON or request contract |
| `SESSION_FORBIDDEN` | 403 | Session belongs to another user |
| `SESSION_NOT_FOUND` | 404 | Unknown session UUID |
| `SESSION_EXPIRED` | 410 | Retention period ended |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | JSON required |
| `AGENT_UNAVAILABLE` | 503 | Runtime failed without safe response |

The current API calls `StudentAgentRuntime`, which is the ADK root-Agent
runtime. As the existing planner/tool/validator chain is assembled into the
root runtime, its `ValidatedResponse` already fits this same API contract; the
browser contract does not need to change.
