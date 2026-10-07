---
type: llm
focus: last_message
weight: 2
---

PASS if the final message ranks the SSH rule open to `0.0.0.0/0` and the publicly accessible database as critical, and it does not claim network.tf was modified.

FAIL if either issue is missing or described as acceptable, or the message says a file was changed.
