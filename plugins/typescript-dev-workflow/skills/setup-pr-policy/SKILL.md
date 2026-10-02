---
name: setup-pr-policy
description: Install a PR policy into a JavaScript/TypeScript repo — no unresolved TODOs, passing unit tests, >= 80% coverage on changed files, JSDoc on changed exports, and README/docs updates — enforced by a check script and a GitHub Actions workflow, with optional branch protection. Use when the user asks to set up PR checks, PR rules, a PR policy, coverage gates, or required checks for a repository.
---

# Set up the PR policy

Installs these rules into the current repository:

1. No unresolved `TODO` comments in changed source or test files.
2. All unit tests pass.
3. Every changed source file has >= 80% coverage (lines, statements, functions, branches).
4. Every exported declaration in a changed source file has a JSDoc (`/** ... */`) comment.
5. A PR that changes source files also updates `README.md` or `docs/**`.

The rules are enforced by `templates/check-pr.mjs` (next to this file), which runs in CI through
`templates/pr-checks.yml`. Companion skills: `/typescript-dev-workflow:generate-jest-tests`
(rule 3) and `/shared-dev-workflow:generate-docs` (rules 4–5).

## 1. Inspect the project

Work out each of these from the repo, not from assumptions. Ask the user only when the repo
doesn't say.

- **Package manager:** check `packageManager` in `package.json`, then lockfiles
  (`pnpm-lock.yaml`, `package-lock.json`, `yarn.lock`).
- **Node version:** check `.nvmrc`, `engines.node`, `.devcontainer`, or the existing CI config.
  Default to the current LTS.
- **Base branch:** `git symbolic-ref --short refs/remotes/origin/HEAD` (strip `origin/`).
- **Source and test directories:** usually `src` and `tests`. Also check for `lib`, `test`,
  `__tests__`, or tests placed next to the source files.
- **Test runner and coverage config:** Jest (`jest.config.*`, `"jest"` in `package.json`),
  Vitest (`vitest.config.*`, `vite.config.*`), or something else. Note any global
  `coverageThreshold`.
- **Existing setup:** look for `scripts/check-pr.mjs`, `.github/workflows/*`,
  `.github/pull_request_template.md`, and a PR section in `CLAUDE.md`. If the policy is
  already partly installed, update it in place rather than duplicating it.

If there is no test runner yet, stop and ask the user which one to add. Don't pick one for them.

## 2. Install the check script

- Copy `templates/check-pr.mjs` to `scripts/check-pr.mjs`, unchanged. Its header documents
  the configuration environment variables.
- If the source or test directories differ from `src` and `tests`, set `PR_SOURCE_DIRS` and
  `PR_TEST_DIRS` in the `check:pr` script below rather than editing the file. That keeps it
  identical to the template, so it's easy to update.

## 3. Add package.json scripts

Add a `test:pr` script that runs the whole suite with coverage and writes
`coverage/coverage-summary.json` (the istanbul `json-summary` format), and a `check:pr` script:

- **Jest:** `jest --coverage --coverageReporters=text --coverageReporters=json-summary`.
  Keep whatever flags the existing `test` script needs (for example
  `node --experimental-vm-modules`).
- **Vitest:** `vitest run --coverage --coverage.reporter=text --coverage.reporter=json-summary`
  (needs `@vitest/coverage-v8`; ask before adding the dependency).
- **`check:pr`:** `node scripts/check-pr.mjs`, prefixed with `PR_SOURCE_DIRS=` and
  `PR_TEST_DIRS=` only if needed.

If the project has a global coverage threshold that the whole codebase doesn't meet yet,
override it in `test:pr` only. The check script enforces coverage per changed file, so the
global threshold would otherwise fail every PR.

Coverage must include files that no test imports, or untested files are silently skipped.
The script counts a missing file as 0%, so this only affects the coverage report.

## 4. Install the workflow

Copy `templates/pr-checks.yml` to `.github/workflows/pr-checks.yml` and fill in the
placeholders:

| Placeholder             | Value                                                                  |
| ----------------------- | ---------------------------------------------------------------------- |
| `__BASE_BRANCH__`       | Base branch from step 1                                                |
| `__NODE_VERSION__`      | Node version from step 1                                               |
| `__PACKAGE_MANAGER__`   | `pnpm`, `npm`, or `yarn`                                               |
| `__INSTALL_COMMAND__`   | `pnpm install --frozen-lockfile`, `npm ci`, or `yarn install --immutable` |

Keep `pnpm/action-setup` only for pnpm. Don't rename the job: `pr-checks` is the name that
branch protection requires.

## 5. Document the policy

- **`CLAUDE.md`:** add (or create the file with) a `## Pull request rules` section listing the
  five rules, the `test:pr` and `check:pr` commands, pointers to the
  `/typescript-dev-workflow:generate-jest-tests` and `/shared-dev-workflow:generate-docs` skills,
  and this line: "Do not create a PR, or declare PR-bound work finished, while `check:pr` fails."
- **`README.md`:** add a short "Pull Request Requirements" section with the same rules and
  commands, in the README's existing style.
- **`.github/pull_request_template.md`:** add a checklist with one item per rule. If a template
  already exists, append the items to it.

## 6. Verify

- Run `test:pr`, then `check:pr`. Failures on an existing branch are expected. Report them
  (TODOs, coverage gaps, missing JSDoc) rather than fixing them unasked.
- Confirm the script itself works: it ran, found the expected changed files, and read the
  coverage summary.

## 7. Branch protection (ask first)

Branch protection changes the GitHub repository's settings, so ask before applying it. If the
user agrees and `gh` is authenticated with admin rights, run this, substituting the owner, repo,
and base branch:

```bash
gh api -X PUT repos/OWNER/REPO/branches/BASE/protection --input - <<'JSON'
{
  "required_status_checks": { "strict": true, "checks": [{ "context": "pr-checks" }] },
  "enforce_admins": true,
  "required_pull_request_reviews": { "required_approving_review_count": 0 },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
```

Check for existing protection first (`gh api repos/OWNER/REPO/branches/BASE/protection`), and
don't overwrite settings the user didn't ask to change. On a team repo, ask how many approvals
to require. Private repos on the GitHub Free plan don't support branch protection; if the API
returns 403, tell the user.

Remind the user that the required check only reports after the workflow file reaches GitHub, so
the PR that adds the workflow must pass it too.
