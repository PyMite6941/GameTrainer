"""
Capture-card driver helper: which modes does the card offer, and which is best?

Capture cards are standard UVC devices, so no vendor driver is needed on Linux,
Windows 10+ or macOS. What does vary is the list of modes (format, size, fps).
On Linux, `v4l2-ctl` (package v4l-utils) lists them; best_mode() picks the
setting GameTrainer should request in device_config.json:

    prefer MJPG (fits through USB), then 1920x1080, then the highest fps <= 60.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class CaptureMode:
    fourcc: str
    width: int
    height: int
    fps: float

    def as_config(self) -> dict:
        return {"fourcc": self.fourcc, "width": self.width, "height": self.height, "fps": int(round(self.fps))}

    def __str__(self) -> str:
        return f"{self.fourcc} {self.width}x{self.height} @ {self.fps:g} fps"


def parse_v4l2_formats(text: str) -> List[CaptureMode]:
    """Parse `v4l2-ctl --list-formats-ext` output."""
    modes: List[CaptureMode] = []
    fourcc: Optional[str] = None
    size: Optional[tuple] = None
    for line in text.splitlines():
        m = re.search(r"\[\d+\]:\s*'(\w{3,4})'", line)
        if m:
            fourcc, size = m.group(1), None
            continue
        m = re.search(r"Size:\s*\w+\s+(\d+)x(\d+)", line)
        if m:
            size = (int(m.group(1)), int(m.group(2)))
            continue
        m = re.search(r"\(([\d.]+)\s*fps\)", line)
        if m and fourcc and size:
            modes.append(CaptureMode(fourcc, size[0], size[1], float(m.group(1))))
    return modes


def list_modes(index: int) -> List[CaptureMode]:
    """Modes for /dev/video<index>; empty when v4l2-ctl is unavailable (non-Linux, not installed)."""
    if not sys.platform.startswith("linux") or not shutil.which("v4l2-ctl"):
        return []
    try:
        out = subprocess.run(
            ["v4l2-ctl", "-d", f"/dev/video{index}", "--list-formats-ext"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    return parse_v4l2_formats(out.stdout) if out.returncode == 0 else []


def best_mode(modes: List[CaptureMode], max_fps: float = 60.0) -> Optional[CaptureMode]:
    if not modes:
        return None

    def score(m: CaptureMode):
        return (
            m.fourcc == "MJPG",
            (m.width, m.height) == (1920, 1080),
            min(m.width * m.height, 1920 * 1080),
            m.fps if m.fps <= max_fps + 0.5 else 0,
        )

    return max(modes, key=score)


class CaptureCardDriver:
    """Mode discovery for one capture card."""

    def __init__(self, index: int = 0):
        self.index = index

    def modes(self) -> List[CaptureMode]:
        return list_modes(self.index)

    def recommended(self) -> Optional[CaptureMode]:
        return best_mode(self.modes())
