#!/bin/bash
# Run GameTrainer's checks: system readiness, then the end-to-end verification.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
PY="${PYTHON:-$( [[ -x .venv/bin/python ]] && echo .venv/bin/python || echo python3 )}"
"$PY" check_system.py --no-devices
"$PY" verify_tracker.py
