---
type: llm
focus: last_message
weight: 2
---

PASS if the final message ranks all three of these: dropping `legacy_code` (or the `orders.legacy_code` column), an empty or missing `downgrade`, and adding `status` as NOT NULL without a default. It must not claim a file was written or that the migration was applied.

FAIL if any of those three is missing, or the message says a file was changed.
