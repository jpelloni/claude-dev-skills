---
name: review-api-contract
description: Review changed HTTP handlers against the project's existing API contract for missing auth, inconsistent error shapes, wrong status codes, unbounded lists, and breaking request or response changes. Report ranked findings. Apply patches only when the user asks. Do not invent an OpenAPI document. Use when the user asks to review an API contract, check a route against OpenAPI, look for breaking API changes, or invokes /review-api-contract.
---

# Review the API contract

Reviews HTTP handlers in the repository against the contract already in the tree and produces
a ranked findings report. Scope is files on disk — no live HTTP calls, no starting the
server, no generating a new OpenAPI document. Project-specific rules in `CLAUDE.md` or the
existing API section of the README always override the defaults here.

**Do not auto-apply patches.** Propose a handler or spec diff, then ask before writing files.
Never silently change an API.

**Do not invent a contract.** If the repo has no OpenAPI, Swagger, or schema file, review
handlers against each other and against `CLAUDE.md`, and say there is nothing checked in to
diff. Do not create `openapi.yaml`. Writing a spec is a separate task the user has to ask for.

## 1. Find the target files

- If the user named files or a directory, use those and skip the rest of this step.
- Otherwise find the base branch: the ref the user gives, or
  `git symbolic-ref --short refs/remotes/origin/HEAD`. Then collect everything changed against
  it, including uncommitted and untracked work:

  ```bash
  git diff --name-only --diff-filter=ACMR --merge-base <base>
  git ls-files --others --exclude-standard
  ```

- **Include** route handlers and contract files from that set (or from the user-named scope):
  - Express, Fastify, NestJS, Flask, FastAPI, and similar handlers (decorators, `router.get`,
    `@app.route`, `@router.post`, controller methods).
  - Checked-in contracts: `openapi.yaml`, `openapi.yml`, `openapi.json`, `swagger.yaml`,
    `swagger.json`, and a schema the README or `CLAUDE.md` names as the contract.
- When a changed handler calls a helper for auth, errors, or pagination, read that helper even
  if it is unchanged. Read the whole handler, not only the diff hunk.
- Skip tests, lockfiles, and generated clients unless the user names them.
- If the change has no HTTP handlers and no contract file, say so and stop. If the API is
  GraphQL or gRPC only, say so and stop. Do not force REST rules onto it.

## 2. Learn the contract

Read these before scoring findings:

- **Project rules:** `CLAUDE.md` and any README / `docs/**` section on the API, auth, errors,
  or pagination. Note the auth dependency, the error body, success status codes, and which
  routes are meant to be public.
- **The checked-in contract**, when one exists. If several exist, use the one the project
  points at. If the project generates the spec from code (FastAPI `openapi()`, NestJS, a
  zod-to-openapi script, tsoa) and nothing is checked in, there is no contract file to diff.
- **One peer handler** that already matches the rules (a list route that returns a page, a
  mutation that uses the auth dependency). Match that shape in suggested patches.
- Prefer project rules over generic REST advice when they conflict.

## 3. Analyze each target

Pair each changed operation (method + path) with the contract operation of the same method
and path. If the handler's path is a framework pattern (`/items/:id`, `/items/{id}`), treat
those as the same path. Rank each finding **critical**, **warn**, or **note**.

### Breaking contract drift

Compare only fields, status codes, and parameters you can see in the handler and the spec.
If a field is built by a function you have not read, say so instead of guessing its shape.

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| Response drops, renames, or retypes a field the spec still returns | critical | Existing clients break |
| Success status in the handler differs from the spec (`200` where the spec says `201`) | critical | Clients branch on the status |
| New required request field, or a request field the spec marks required and the handler ignores | critical | Old clients are rejected, or the handler accepts a body the contract forbids |
| New optional response field | note | Compatible addition. Mention it. Do not demand it be removed |
| Handler path or method with no contract operation | warn | Drift. Do not invent the missing operation |
| Contract operation with no handler in the tree | warn | Stale spec. Confirm the handler is not in an unread file before flagging it |

### Auth, errors, pagination

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| POST, PUT, PATCH, or DELETE with no auth dependency while the spec sets `security` or peer mutations use the project's auth dependency | critical | Unauthenticated write |
| GET or HEAD the spec marks with `security`, and the handler has none | critical | Unauthenticated read of a protected resource |
| Health, metrics, or docs routes left public | note | Often intentional. Do not add auth |
| Error body differs from the project's error helper (`{ok: false}` or a bare string where peers return `{error: {code, message}}`) | warn | Clients cannot parse failures |
| Failure returned as `200`, or a validation error returned as `500` | warn | Callers treat failure as success, or retry a bad request |
| List handler returns a raw array where the spec or peer lists return a page (`items` plus a cursor or page) | critical when the spec requires the page, otherwise warn | Clients lose pagination and the handler can load the whole table |
| List handler has no limit and the project already paginates other lists | warn | Unbounded read |

### What not to flag

- A route that `CLAUDE.md` and the spec both leave unauthenticated.
- An optional response field that was added.
- A comment that disagrees with the code. Review the code.
- A generated client under `node_modules` or a build directory.

**Out of scope:** writing a new OpenAPI file, GraphQL and gRPC, calling the running service,
and applying patches without confirmation.

## 4. Report findings

Produce a ranked report. For each finding include:

1. **Location** — file path, method, and path (`POST /items`).
2. **Severity** — critical / warn / note.
3. **Why it hurts** — one or two sentences, naming the contract field or peer handler.
4. **Tighter alternative** — the status, auth dependency, or response shape that matches the
   spec or the peer. Quote the spec path. Do not invent fields that are in neither.

Group by severity (critical first). If there is no checked-in contract, say that once at the
top and review only handler-to-handler consistency.

## 5. Suggest patches (ask before applying)

- Propose a handler change or a spec change, and say which one it is. A breaking code change
  that the spec already allows is a handler fix. A spec that is simply behind an intentional
  change is a spec fix. Ask which the user wants when it is not obvious.
- Ask the user which findings to apply. Write files only for the ones they confirm.
- Never silently edit handlers or the contract.

## 6. Hand back

Summarize:

- Counts by severity (critical / warn / note).
- Files reviewed; files changed only if patches were applied.
- Whether a checked-in contract was found, and any operations you could not pair because a
  helper or another router file was outside the tree you read.
- Remind that this review does not call the service. A contract test or a generated client
  check is a separate step when the user wants one.
