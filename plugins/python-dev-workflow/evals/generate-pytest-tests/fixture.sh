#!/usr/bin/env bash
# Seeds the fixture and installs pytest into a local virtualenv.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$here/fixture/." .
python3 -m venv .venv
.venv/bin/pip install --disable-pip-version-check pytest==8.3.4 pytest-cov==6.0.0
