---
type: llm
focus: last_message
weight: 2
---

PASS if the final message ranks both of these as breaking or critical: `GET /items` returning a raw list instead of `{ items, next_cursor }`, and `POST /items` missing auth or returning a status other than 201. It must not claim a file was written or that a new OpenAPI document was created.

FAIL if either break is missing, or the message says a file was changed.
