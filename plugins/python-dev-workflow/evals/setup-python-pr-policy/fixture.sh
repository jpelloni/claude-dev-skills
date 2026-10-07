#!/usr/bin/env bash
# Installs pytest, then records main as origin's default branch so the policy script can resolve a base ref.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$here/fixture/." .
python3 -m venv .venv
.venv/bin/pip install --disable-pip-version-check -e ".[dev]"

git init -b main
git config user.email "eval@example.com"
git config user.name "Eval"
git add .
git commit -m "Initial commit"
git update-ref refs/remotes/origin/main HEAD
git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/main
