---
type: regex
target:
  source: file
  path: .github/workflows/pr-checks.yml
pattern: "__[A-Z_]+__"
match: not_contains
---
