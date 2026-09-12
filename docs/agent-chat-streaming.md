# Agent Chat Streaming API

`POST /api/chat/stream/` accepts the same JSON body as `/api/chat/` and returns
`text/event-stream`. The browser should use `fetch()` and read the response
body because a POST keeps the message out of a URL. Events use SSE `id`,
`event`, and JSON `data` fields.

| Event | Data |
| --- | --- |
| `session` | `session_id`, `stream_id` |
| `progress` | user-facing phase only |
| `answer` | safe answer text |
| `source` / `action` | validated response evidence and registered action |
| `complete` | status, limitations, follow-up question |
| `error` | safe API error only |

Reconnect with `GET /api/chat/streams/{stream_id}/events/?after={last_event_id}`.
The server stores only the latest 32 events for the short-lived conversation
session and verifies the same Django login owner before replaying them.

Cancel with `POST /api/chat/streams/{stream_id}/cancel/`. A run canceled before
the ADK call does not start the call or persist a turn. The current ADK root
runtime is synchronous, so a cancellation arriving during an already-running
provider call prevents further SSE events but cannot yet abort that provider
request; token-level provider cancellation will replace this boundary when the
root runtime exposes an abortable stream.
