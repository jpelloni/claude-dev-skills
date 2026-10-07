---
type: llm
focus: last_message
weight: 2
---

PASS if the final message says the tests for src/greet.js passed and that coverage for that file is at least 80% for lines, statements, functions, and branches.

FAIL if the message says the tests failed, says coverage is below 80%, or never mentions a test run or coverage for src/greet.js.
