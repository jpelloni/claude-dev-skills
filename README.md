# claude-dev-skills

A [Claude Code](https://claude.com/claude-code) plugin marketplace with development-workflow
skills for JavaScript/TypeScript and Python projects, shared cross-language skills
(documentation and GitHub Actions review), and AWS IAM and Terraform security review.

## Plugins

### `shared-dev-workflow`

| Skill                                          | What it does                                                                                                                        |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `/shared-dev-workflow:generate-docs`           | Adds language-aware code docs (JSDoc for JS/TS, docstrings for Python) to changed source files and updates `README.md` / `docs/**` to match. |
| `/shared-dev-workflow:review-github-actions`   | Reviews in-repo GitHub Actions for untrusted checkout, script injection, broad token permissions, unpinned actions, and secret leakage, ranks findings, and suggests YAML patches — applies only when you ask. |

### `typescript-dev-workflow`

| Skill                                          | What it does                                                                                                                        |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `/typescript-dev-workflow:generate-jest-tests` | Writes a full Jest or Vitest suite for a source file, matching the project's layout and ESM/CJS mocking, and iterates until it passes with >= 80% coverage. |
| `/typescript-dev-workflow:setup-pr-policy`     | Installs a PR policy (no TODOs, passing tests, >= 80% coverage on changed files, JSDoc, docs updates), enforced by a check script and a GitHub Actions workflow, with optional branch protection. |

### `python-dev-workflow`

| Skill                                         | What it does                                                                                                                        |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `/python-dev-workflow:generate-pytest-tests`  | Writes a full pytest or unittest suite for a Python source file, matching the project's layout, fixtures, and mocking, and iterates until it passes with >= 80% coverage. |

### `aws-dev-workflow`

| Skill                                               | What it does                                                                                                                        |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `/aws-dev-workflow:review-iam-least-privilege`      | Reviews in-repo IAM (JSON/YAML policies, CloudFormation/SAM `AWS::IAM::*`, Terraform `aws_iam_*`) for least-privilege issues, ranks findings, and suggests tighter patches — applies only when you ask. |
| `/aws-dev-workflow:review-terraform-security`       | Reviews in-repo Terraform for exposure, encryption, backup, and secret issues beyond IAM (public security groups and databases, public buckets, IMDSv1, plaintext secrets), ranks findings, and suggests HCL patches — applies only when you ask. |

The skills read each project's `CLAUDE.md`, README, config, and existing tests, and follow
them. Put project-specific conventions in `CLAUDE.md` rather than editing the skills.

## Installation

In Claude Code:

```text
/plugin marketplace add jpelloni/claude-dev-skills
/plugin install shared-dev-workflow@claude-dev-skills
/plugin install typescript-dev-workflow@claude-dev-skills
/plugin install python-dev-workflow@claude-dev-skills
/plugin install aws-dev-workflow@claude-dev-skills
```

Install à la carte if you only need one language, shared docs, or AWS IAM review.

This repository is private, so installing needs git access to it (your GitHub credentials, or
the credentials VS Code forwards into a devcontainer).

### Enable for everyone working on a project

Commit this to the project's `.claude/settings.json`. Claude Code then prompts anyone who
opens the project, including in a fresh devcontainer, to install the plugins:

```json
{
  "extraKnownMarketplaces": {
    "claude-dev-skills": {
      "source": { "source": "github", "repo": "jpelloni/claude-dev-skills" }
    }
  },
  "enabledPlugins": {
    "shared-dev-workflow@claude-dev-skills": true,
    "typescript-dev-workflow@claude-dev-skills": true,
    "python-dev-workflow@claude-dev-skills": true,
    "aws-dev-workflow@claude-dev-skills": true
  }
}
```

### Migration from `dev-workflow`

The former `dev-workflow` plugin is renamed to `typescript-dev-workflow`. Update projects that
still reference the old id:

- Plugin id: `dev-workflow` → `typescript-dev-workflow`
- Skill invocations: `/dev-workflow:*` → `/typescript-dev-workflow:*`
- Documentation skill: `/dev-workflow:generate-docs` → `/shared-dev-workflow:generate-docs`
- In `.claude/settings.json`, replace `dev-workflow@claude-dev-skills` with
  `typescript-dev-workflow@claude-dev-skills` and add `shared-dev-workflow@claude-dev-skills`
  if you use generate-docs

## Updating

Bump `version` in the relevant
`plugins/<plugin>/.claude-plugin/plugin.json` and push. Projects pick up the change with
`/plugin marketplace update claude-dev-skills`.

`skills/setup-pr-policy/templates/check-pr.mjs` (under `typescript-dev-workflow`) is the
canonical copy of the PR check script. Projects get a copy at setup time, so to roll out a fix,
re-run `setup-pr-policy` in each project or copy the file over.

## Evals

`claude plugin validate` checks manifests only. Behavior checks live in each plugin's
`evals/` directory and run with `claude plugin eval` from that plugin's root. Each case
starts in an empty workspace, so the plugin does not need to be installed into another repo.

Every case sets `runs: 1`. Pass `--scaffold` so `fixture.sh` can seed the workspace. Add
`--ablation none` while iterating. Results land in that plugin's `evals/results/` and are
gitignored. The pytest case needs `python3-venv` on the machine that runs the scaffold.

| Case | Plugin directory | Extra flags |
| --- | --- | --- |
| `generate-docs` | `plugins/shared-dev-workflow` | `--allow-tools Write Edit "Bash(git *)"` |
| `review-github-actions` | `plugins/shared-dev-workflow` | none |
| `generate-jest-tests` | `plugins/typescript-dev-workflow` | `--allow-tools Write Edit "Bash(npm *)"` |
| `setup-pr-policy` | `plugins/typescript-dev-workflow` | `--allow-tools Write Edit "Bash(npm *)" "Bash(node *)" "Bash(git *)"` |
| `generate-pytest-tests` | `plugins/python-dev-workflow` | `--allow-tools Write Edit "Bash(.venv/bin/pytest *)" "Bash(python *)" "Bash(python3 *)"` |
| `review-iam-least-privilege` | `plugins/aws-dev-workflow` | none |
| `review-terraform-security` | `plugins/aws-dev-workflow` | none |

```bash
cd plugins/aws-dev-workflow
claude plugin eval . \
  --trust-plugin \
  --scaffold \
  --case review-terraform-security \
  --no-publish
```

## Validating

The `validate` workflow runs these on every PR and is required to merge into `main`:

```bash
claude plugin validate .
claude plugin validate plugins/shared-dev-workflow
claude plugin validate plugins/typescript-dev-workflow
claude plugin validate plugins/python-dev-workflow
claude plugin validate plugins/aws-dev-workflow
```
