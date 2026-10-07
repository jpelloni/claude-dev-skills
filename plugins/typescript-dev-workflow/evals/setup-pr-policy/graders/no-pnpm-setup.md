---
type: regex
target:
  source: file
  path: .github/workflows/pr-checks.yml
pattern: pnpm/action-setup
match: not_contains
---
