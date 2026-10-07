#!/usr/bin/env bash
# Seeds the workspace, commits the base project, then leaves src/greet.js untracked.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$here/fixture/." .

hold="$(mktemp -d)"
mv src/greet.js "$hold/greet.js"

git init -b main
git config user.email "eval@example.com"
git config user.name "Eval"
git add .
git commit -m "Initial commit"
git update-ref refs/remotes/origin/main HEAD
git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/main

mv "$hold/greet.js" src/greet.js
rmdir "$hold"
