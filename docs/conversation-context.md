# Conversation session and follow-up context

`ConversationSession.session_id` is the identifier passed to the future ADK
session service. Django owns ownership, expiry, turn ordering, and the safe
history projection. ADK owns transient model events only. A raw student number
or login identifier is never written here; `subject_key` is an HMAC-SHA256
value derived from the authenticated server-side subject.

## Retention and size

- A session expires 24 hours after creation. It cannot be read or resumed once
  expired.
- Messages are capped at 2,000 characters and response metadata at 4,000.
- Only the latest 12 turns are retained. The resolver sees at most 500
  characters of each retained turn.
- Turn insertion takes a database row lock, assigns the next sequence, then
  increments the session version. Concurrent requests therefore cannot claim
  the same turn sequence.

## Follow-up resolution

The server derives candidates from prior user exchanges and their adjacent
assistant reply. The Follow-up Resolver can only select a supplied turn ID; it
cannot create facts, URLs, menus, or history. A reference is accepted only if
the ID is currently valid and its confidence is at least 0.78. Otherwise the
server asks a fixed clarification question instead of guessing.

Issue #33 may use an accepted reference to rewrite a search query. It must not
use a model-produced reference unless this policy has validated it first.
