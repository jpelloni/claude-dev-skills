---
name: review-github-actions
description: Review in-repo GitHub Actions workflows and composite actions for untrusted-code risks, overly broad token permissions, unpinned actions, secret leakage, and missing timeouts or concurrency. Report ranked findings with suggested YAML patches. Apply patches only when the user asks. Use when the user asks to review GitHub Actions, workflow security, pull_request_target, action pinning, or invokes /review-github-actions.
---

# Review GitHub Actions

Reviews GitHub Actions definitions in the repository and produces a ranked findings report
with suggested tighter YAML. Scope is files on disk — no live GitHub settings API, no
rerunning workflows, no changing branch protection. Project-specific rules in `CLAUDE.md`
or existing workflow conventions always override the defaults here.

**Do not auto-apply patches.** Propose revised YAML, then ask before writing files. Never
silently change CI.

**Do not invent commit SHAs.** When a finding says to pin an action, name the `owner/repo`
and the tag to resolve. The user (or a lookup they ask for) supplies the 40-character SHA.
Never write a made-up hash into a workflow.

Installing a new PR-policy workflow is `/typescript-dev-workflow:setup-pr-policy`. This
skill reviews workflows that already exist.

## 1. Find the target files

- If the user named files or a directory, use those and skip the rest of this step.
- Otherwise find the base branch: the ref the user gives, or
  `git symbolic-ref --short refs/remotes/origin/HEAD`. Then collect everything changed against
  it, including uncommitted and untracked work:

  ```bash
  git diff --name-only --diff-filter=ACMR --merge-base <base>
  git ls-files --others --exclude-standard
  ```

- **Include** from that set (or from the user-named scope):
  - `.github/workflows/*.{yml,yaml}`
  - Composite or JS actions: `.github/actions/**/action.yml` and a root `action.yml` when
    this repo is itself an action
  - Reusable workflows called with `uses: ./.github/workflows/...` — read the callee even
    if it is unchanged
- Skip app source, lockfiles, and docs unless they are the workflow files above.
- If the repo has no GitHub Actions files, say so and stop. If CI lives in GitLab,
  CircleCI, or another system, name that and stop. Do not rewrite it into GitHub Actions.

## 2. Learn project conventions

Read these before scoring findings:

- **Project rules:** `CLAUDE.md` and any README / `docs/**` section on CI or release.
  Note allowed actions, a required permissions block, whether tags are an accepted pin,
  and which workflows are allowed to deploy.
- **Existing patterns:** one tight workflow in the same repo (least permissions, pinned
  actions, a timeout). Match that style in suggested patches.
- Prefer project rules over generic advice when they conflict. If the project documents
  major-version tags (`@v4`) as the pin, do not raise them above **note**.

## 3. Analyze each target

Read the whole workflow, not only the diff hunk. A permissions block at the top of the file
covers jobs that the diff did not touch. Resolve `uses: ./.github/workflows/...` callees
that are in the tree. For `uses: owner/repo/.github/workflows/foo.yml@ref` whose source is
not in this repo, review the caller's `secrets`, `permissions`, and `with` inputs, and mark
the callee body needs-human-review.

Rank each finding **critical**, **warn**, or **note**. Group repeated hits of the same
pattern (every `actions/checkout@v4` in one file) into one finding that lists the steps.

### Untrusted code and events

These contexts are attacker-controlled on `pull_request`, `pull_request_target`,
`issues`, `issue_comment`, `workflow_run` from a PR, and `workflow_dispatch` inputs:
`github.event.pull_request.title`, `.body`, `github.event.issue.title`, `github.event.comment.body`,
`github.head_ref`, `github.event.pull_request.head.ref`, `github.event.pull_request.head.sha`,
and `github.event.inputs.*`.

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| `pull_request_target` (or `workflow_run`) checks out the PR head (`ref:` / `github.event.pull_request.head.sha` or `head.ref`) and has a write token or any secret | critical | Untrusted code runs with the base repository token and secrets |
| `pull_request_target` that only reads the base ref (labels, comments) and never checks out or runs PR code | note | Often a safe bot. Confirm it never executes a PR script |
| Untrusted context interpolated into `run:` or into `actions/github-script` `script:` (`run: echo "${{ github.event.pull_request.title }}"`) | critical | Shell or JS injection from a PR title, branch name, or comment |
| The same value passed through `env:` and used as `"$VAR"` in the script | note | This is the safe form. Do not flag it |
| `runs-on: self-hosted` (or a self-hosted label) for `pull_request` / `pull_request_target` from outside collaborators | critical | Untrusted code on a persistent runner can steal credentials of later jobs |
| `secrets: inherit` on a reusable-workflow call triggered by an untrusted event | warn | Every secret in the caller is exposed to the callee |

### Token permissions

GitHub's default `GITHUB_TOKEN` is read-only on some repositories and permissive on others.
A missing `permissions` key leaves the token at that repository or organization default.
Score it as **warn** and needs-human-review.

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| `permissions: write-all`, or workflow-level `contents: write` / `packages: write` on a job that runs untrusted PR code | critical | A malicious PR can push to the repo or publish a package |
| No `permissions` key at workflow or job level | warn | Depends on the org or repo default, which is not in the file. Say needs-human-review for that default, and suggest an explicit `permissions: contents: read` plus job-level additions |
| `id-token: write` on a job that also checks out untrusted PR code | critical | OIDC can assume a cloud role from attacker-controlled steps |
| `id-token: write` on a trusted deploy job (push to the default branch, `environment:`) | note | Expected for cloud auth. Do not drop it |
| `security-events: write` on a CodeQL or upload-SARIF job | note | Expected. Do not flag it |
| `pull-requests: write` only on the job that comments or labels | note | Fine when it is not granted to the whole workflow |

Suggest the narrowest job-level block that still lets the job succeed. Do not widen a
permission while fixing something else.

### Actions and pinning

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| `uses: owner/repo@main`, `@master`, `@latest`, or a floating branch | critical | The action can change under you and run new code in CI |
| `uses: owner/repo@v4` (moving major tag) when the project has not accepted tag pins | warn | Tags can be moved. The tight form is a full commit SHA with the tag in a comment |
| `uses: docker://image:tag` with no digest | warn | Same mutable-tag problem for a container action |
| A third-party action (not `actions/*`, `github/*`, or an org the project already uses) | note | New supply-chain dependency. Name it; do not delete it without asking |
| `actions/checkout` with default `persist-credentials: true` followed by a third-party action or a script from the PR | warn | The checkout token sits in `.git` for later steps. Suggest `persist-credentials: false` when the job does not push |

### Secrets in logs and files

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| `run` echoes a secret (`echo ${{ secrets.FOO }}`, `echo "$AWS_SECRET_ACCESS_KEY"`) or prints the whole `github.event` payload | critical | Secrets land in logs. Debug logs expand masked values poorly |
| A secret written into `$GITHUB_ENV`, `$GITHUB_OUTPUT`, or a workspace file that a later step archives | warn | Artifacts and later jobs can capture it |
| Static cloud keys (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`) on a deploy job when the repo is AWS | note | Prefer OIDC (`id-token: write` and a role to assume). Do not rewrite the auth flow unless the user asks |
| `set-output` or the deprecated `::set-output` command | note | Correctness, not a secret leak by itself |

### Timeouts, concurrency, and cache

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| No `timeout-minutes` on a `self-hosted` job or a deploy job | warn | A stuck job holds the runner or a production lock |
| No `timeout-minutes` on a `ubuntu-latest` test job | note | Worth setting from the job's usual duration. Do not invent a short number |
| A deploy workflow with no `concurrency` group | warn | Two releases can run at once |
| `cancel-in-progress: true` on a deploy | warn | Cancelling mid-deploy leaves the environment half-applied. Suggest a group without cancel |
| A test workflow with no concurrency | note | Suggest a group keyed by workflow and ref only when overlapping runs are wasteful |
| `actions/cache` or `actions/setup-*` cache on `pull_request` whose key is also restored on the default branch, with no scope that isolates PR caches | warn | A PR can poison the cache that `main` restores |

### What not to flag

- `actions/checkout` of the push or of `github.ref` on a `push` to a protected branch.
- `permissions: contents: read` at workflow level with a tighter or slightly wider job block.
- Untrusted text passed only through `env:` and referenced as a shell variable.
- A job allowed to comment on pull requests when `CLAUDE.md` says so, with `pull-requests: write` only on that job. Mark a broader grant **warn**.

**Out of scope:** branch protection and required checks (use
`/typescript-dev-workflow:setup-pr-policy` when the user wants those installed), org
allow-lists and default token settings that are not in the repo,
rerunning or cancelling live runs, and applying patches without confirmation.

## 4. Report findings

Produce a ranked report. For each finding include:

1. **Location** — file path, job id, and step name or `uses` line.
2. **Severity** — critical / warn / note.
3. **Why it hurts** — one or two sentences.
4. **Tighter alternative** — concrete YAML. For a pin, show `uses: owner/repo@<full-sha> # v4.x.y` and say the SHA still has to be looked up. Do not fill in a hash you did not read from the repo or from a source the user supplied.

Group by severity (critical first). If a `pull_request_target` workflow is documented as a
label bot and does not run PR code, mark it **note** / needs-human-review rather than
rewriting the trigger.

## 5. Suggest patches (ask before applying)

- Propose revised YAML that matches the file's style (quote style, `permissions` placement,
  whether steps use `name:`).
- A new top-level `permissions` or `concurrency` block is still a suggestion. Call it out
  and ask before adding it.
- Ask the user which findings to apply. Write files only for the ones they confirm.
- Never silently edit workflows in the working tree.

## 6. Hand back

Summarize:

- Counts by severity (critical / warn / note).
- Files reviewed; files changed only if patches were applied.
- Residual risks and needs-human-review items: the repository's default `GITHUB_TOKEN`
  permissions, reusable workflows whose bodies are not in this repo, action SHAs that were
  not looked up, self-hosted runner labels whose fleet you cannot see.
- Remind that this review is in-repo only. Org Actions policies and branch protection are
  separate checks when the user wants them.
