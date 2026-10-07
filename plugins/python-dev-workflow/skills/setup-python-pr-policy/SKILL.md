---
name: setup-python-pr-policy
description: Install a PR policy into a Python repo — no unresolved TODOs, passing pytest or unittest, >= 80% line and branch coverage on changed files, docstrings on public functions and classes, and README/docs updates — enforced by a check script and a GitHub Actions workflow, with optional branch protection. Use when the user asks to set up Python PR checks, pytest coverage gates, docstring checks, or required checks for a Python repository, or invokes /setup-python-pr-policy.
---

# Set up the Python PR policy

Installs these rules into the current repository:

1. No unresolved `TODO` comments in changed source or test files.
2. All unit tests pass.
3. Every changed source file has >= 80% line and branch coverage.
4. Every public function, class, and public method in a changed source file has a docstring. A module docstring is required when the file defines at least one of those. Names starting with `_` are private.
5. A PR that changes source files also updates `README.md` or `docs/**`.

The rules are enforced by `templates/check_pr.py` (next to this file), which runs in CI through
`templates/pr-checks.yml`. Companion skills: `/python-dev-workflow:generate-pytest-tests`
(rule 3) and `/shared-dev-workflow:generate-docs` (rules 4–5).

This skill is for Python projects. If the repo is JavaScript or TypeScript and has no Python
package, stop and point the user at `/typescript-dev-workflow:setup-pr-policy`.

coverage.py does not report function coverage the way Istanbul does. Do not invent that
metric. Line and branch coverage are the gate.

## 1. Inspect the project

Work out each of these from the repo, not from assumptions. Ask the user only when the repo
doesn't say.

- **Python version:** `.python-version`, then `requires-python` in `pyproject.toml`, then the
  version already pinned in CI. If none of those exist, ask. Don't pick one.
- **Installer:** Poetry (`poetry.lock`), uv (`uv.lock`), PDM (`pdm.lock`), Pipenv
  (`Pipfile.lock`), Hatch, or pip (`requirements*.txt` and `pyproject.toml`).
- **How tasks are run:** a Makefile, tox, nox, Hatch scripts (`[tool.hatch.envs.*.scripts]`),
  or PDM scripts (`[tool.pdm.scripts]`).
- **Base branch:** `git symbolic-ref --short refs/remotes/origin/HEAD` (strip `origin/`).
- **Source and test directories:** usually `src` and `tests`. Also check for a package at the
  repo root, `test`, or tests next to the source. Note `testpaths` and `pythonpath`.
- **Test runner:** pytest (`pytest.ini`, `[tool.pytest.ini_options]`, `conftest.py`) or
  unittest. Note whether coverage is already configured (`[tool.coverage.*]`, `.coveragerc`,
  pytest-cov).
- **Existing setup:** look for `scripts/check_pr.py`, `.github/workflows/*`,
  `.github/pull_request_template.md`, and a PR section in `CLAUDE.md`. If the policy is
  already partly installed, update it in place rather than duplicating it.

If there is no test runner yet, stop and ask the user which one to add. Don't pick one for them.
If pytest-cov (or coverage.py) is not already a dependency, ask before adding it.

## 2. Install the check script

- Copy `templates/check_pr.py` to `scripts/check_pr.py`, unchanged. Its header documents the
  configuration environment variables.
- If the source or test directories differ from `src` and `tests`, set `PR_SOURCE_DIRS` and
  `PR_TEST_DIRS` on the `check-pr` command below rather than editing the file. That keeps it
  identical to the template, so it's easy to update.

## 3. Add the local commands

Add a `test-pr` command that runs the whole suite with branch coverage and writes
`coverage/coverage.json`, and a `check-pr` command that runs `python scripts/check_pr.py`.

Put them on the task runner the project already uses. If it has none, add a Makefile:

- **pytest:** `pytest --cov --cov-branch --cov-report=term --cov-report=json:coverage/coverage.json`.
  Keep the project's existing addopts and `pythonpath`. Set `--cov` to the source package or
  `PR_SOURCE_DIRS` when the project doesn't already name a source.
- **unittest:** `coverage run --branch -m unittest discover` and then
  `coverage json -o coverage/coverage.json`. Ask before adding the `coverage` dependency.
- **`check-pr`:** `python scripts/check_pr.py`, with `PR_SOURCE_DIRS` and `PR_TEST_DIRS`
  prefixed only when the directories differ from `src` and `tests`.

`--cov-branch` is required. A report without branch data fails the check.

If the project has a global fail-under that the whole codebase doesn't meet yet, don't let
that fail `test-pr`. The check script enforces coverage per changed file.

## 4. Install the workflow

Copy `templates/pr-checks.yml` to `.github/workflows/pr-checks.yml` and fill in the
placeholders:

| Placeholder          | Value                                                                 |
| -------------------- | --------------------------------------------------------------------- |
| `__BASE_BRANCH__`    | Base branch from step 1                                               |
| `__PYTHON_VERSION__` | Python version from step 1, without a `>=` range                      |
| `__INSTALL_COMMAND__`| The project's frozen install (`poetry install --no-interaction`, `uv sync --frozen`, `pip install -r requirements.txt`, `pip install -e ".[dev]"`, or the equivalent already used in CI) |
| `__TEST_COMMAND__`   | The `test-pr` command from step 3                                     |

Add a Poetry or uv setup step only when that is the installer. Don't rename the job:
`pr-checks` is the name that branch protection requires.

## 5. Document the policy

- **`CLAUDE.md`:** add (or create the file with) a `## Pull request rules` section listing the
  five rules, the `test-pr` and `check-pr` commands, pointers to the
  `/python-dev-workflow:generate-pytest-tests` and `/shared-dev-workflow:generate-docs` skills,
  and this line: "Do not create a PR, or declare PR-bound work finished, while `check-pr` fails."
- **`README.md`:** add a short "Pull Request Requirements" section with the same rules and
  commands, in the README's existing style.
- **`.github/pull_request_template.md`:** add a checklist with one item per rule. If a template
  already exists, append the items to it.

## 6. Verify

- Run `test-pr`, then `check-pr`. Failures on an existing branch are expected. Report them
  (TODOs, coverage gaps, missing docstrings) rather than fixing them unasked.
- Confirm the script itself works: it ran, found the expected changed files, and read the
  coverage JSON.

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
