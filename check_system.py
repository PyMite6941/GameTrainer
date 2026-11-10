#!/usr/bin/env python3
"""Check whether this machine is ready to track games (same as `gametrainer --check`).

    python check_system.py               full check, including capture devices
    python check_system.py --no-devices  skip probing video devices
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from middleware.integration.system_check import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
