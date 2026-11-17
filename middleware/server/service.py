"""
Run the dashboard on boot (Linux / Raspberry Pi OS) as a systemd user service.

    gametrainer --install-service [--port 8765] [--output ./data]

writes ~/.config/systemd/user/gametrainer-dashboard.service pointing at this
install (source checkout, pip install, or the one-file binary) and the current
folder's data, then prints the two commands that enable it. Nothing runs as
root and nothing is started without you running those commands.
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path
from typing import List, Optional

UNIT_NAME = "gametrainer-dashboard.service"


def launch_command() -> List[str]:
    """How to start GameTrainer from a service: the binary, or this Python + track_game.py."""
    if getattr(sys, "frozen", False):
        return [sys.executable]
    script = Path(__file__).resolve().parents[2] / "track_game.py"
    return [sys.executable, str(script)]


def unit_text(workdir: Path, port: int, output: str, host: str = "0.0.0.0") -> str:
    cmd = launch_command() + ["--serve", "--host", host, "--port", str(port), "--output", output]
    return f"""[Unit]
Description=GameTrainer dashboard (read-only match history on port {port})
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory={workdir}
ExecStart={" ".join(shlex.quote(c) for c in cmd)}
Restart=on-failure
RestartSec=5
Nice=10

[Install]
WantedBy=default.target
"""


def install_service(port: int = 8765, output: str = "./data", host: str = "0.0.0.0",
                    unit_dir: Optional[Path] = None) -> Path:
    unit_dir = unit_dir or Path.home() / ".config" / "systemd" / "user"
    unit_dir.mkdir(parents=True, exist_ok=True)
    path = unit_dir / UNIT_NAME
    path.write_text(unit_text(Path.cwd(), port, output, host))
    return path
