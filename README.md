# claude-dev-skills

A [Claude Code](https://claude.com/claude-code) plugin marketplace with development-workflow
skills for JavaScript/TypeScript projects.

## Plugins

### `dev-workflow`

| Skill                                  | What it does                                                                                                                        |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `/dev-workflow:generate-jest-tests`    | Writes a full Jest or Vitest suite for a source file, matching the project's layout and ESM/CJS mocking, and iterates until it passes with >= 80% coverage. |
| `/dev-workflow:generate-docs`          | Adds JSDoc to exported declarations in changed files and updates `README.md` / `docs/**` to match.                                  |
| `/dev-workflow:setup-pr-policy`        | Installs a PR policy (no TODOs, passing tests, >= 80% coverage on changed files, JSDoc, docs updates), enforced by a check script and a GitHub Actions workflow, with optional branch protection. |

The skills read each project's `CLAUDE.md`, README, config, and existing tests, and follow
them. Put project-specific conventions in `CLAUDE.md` rather than editing the skills.

## Installation

In Claude Code:

```text
/plugin marketplace add jpelloni/claude-dev-skills
/plugin install dev-workflow@claude-dev-skills
```

This repository is private, so installing needs git access to it (your GitHub credentials, or
the credentials VS Code forwards into a devcontainer).

### Enable for everyone working on a project

Commit this to the project's `.claude/settings.json`. Claude Code then prompts anyone who
opens the project, including in a fresh devcontainer, to install the plugin:

```json
{
  "extraKnownMarketplaces": {
    "claude-dev-skills": {
      "source": { "source": "github", "repo": "jpelloni/claude-dev-skills" }
    }
  },
  "enabledPlugins": {
    "dev-workflow@claude-dev-skills": true
  }
}
```

## Updating

Bump `version` in `plugins/dev-workflow/.claude-plugin/plugin.json` and push. Projects pick up
the change with `/plugin marketplace update claude-dev-skills`.

`skills/setup-pr-policy/templates/check-pr.mjs` is the canonical copy of the PR check script.
Projects get a copy at setup time, so to roll out a fix, re-run `setup-pr-policy` in each
project or copy the file over.

## Validating

```bash
claude plugin validate .
claude plugin validate plugins/dev-workflow
```
