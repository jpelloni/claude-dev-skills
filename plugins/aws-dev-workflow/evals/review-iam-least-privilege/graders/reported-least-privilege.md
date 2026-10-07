---
type: llm
focus: last_message
weight: 2
---

PASS if the final message ranks `AdministratorAccess` on the app role, or the `Principal` of `*`, as critical, and it does not claim iam.tf was modified.

FAIL if both of those issues are missing, either is described as acceptable, or the message says a file was changed.
