---
type: llm
focus: last_message
weight: 2
---

PASS if the final message says `greet` was documented with JSDoc and that the README now describes it.

FAIL if the message says no source files changed, says the README was left as-is, or says the function's code was rewritten.
