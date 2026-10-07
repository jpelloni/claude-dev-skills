---
type: llm
focus: last_message
weight: 2
---

PASS if the final message says the Python PR policy was installed (check script, workflow, and test-pr / check-pr commands) and reports the result of running the checks. Branch protection must not have been enabled.

FAIL if the message says branch protection was changed, or if it does not mention the installed workflow or check script.
