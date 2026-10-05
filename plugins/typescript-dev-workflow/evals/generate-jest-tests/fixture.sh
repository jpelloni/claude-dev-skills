#!/usr/bin/env bash
# Seeds the empty eval workspace with the fixture project and installs Jest.
# Invoked with the workspace as the cwd. The script itself stays in the case directory.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$here/fixture/." .
npm ci
