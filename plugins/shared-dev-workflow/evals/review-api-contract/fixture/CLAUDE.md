# API rules

- The contract is `openapi.yaml`. Do not create another OpenAPI document.
- List endpoints return `{ items, next_cursor }`.
- Mutating routes use the `require_user` dependency.
- Errors return `{ "error": { "code", "message" } }` with a 4xx status.
- Do not modify API files unless I ask.
