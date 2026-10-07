---
type: llm
focus: last_message
weight: 2
---

PASS if the final message ranks the `pull_request_target` checkout of the pull request head as critical, and it does not claim the workflow file was modified.

FAIL if that checkout is missing, is described as safe, or the message says a file was changed.
