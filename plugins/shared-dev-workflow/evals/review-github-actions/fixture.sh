#!/usr/bin/env bash
# Copies the workflow fixture into the empty eval workspace.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$here/fixture/." .
