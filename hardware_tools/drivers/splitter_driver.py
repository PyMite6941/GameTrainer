"""
Splitter setup: the alternative to a passthrough capture card.

If your capture device has no HDMI Out (cheap USB capture sticks), put an HDMI
splitter in front of it:

    console HDMI Out -> splitter In
    splitter Out 1 -> TV                  (you play on this)
    splitter Out 2 -> capture stick -> laptop USB

A splitter needs no driver and no GameTrainer setting - the capture stick is
the device GameTrainer opens. What matters is buying the right splitter.
"""

from __future__ import annotations

from typing import List

CHECKLIST: List[str] = [
    "Use a powered 1-in-2-out splitter (USB- or wall-powered); unpowered ones drop the signal.",
    "Pick one that supports your TV's mode on output 1 and downscales output 2 to 1080p, "
    "so a 4K TV and a 1080p capture stick can both be used.",
    "Splitters do not remove HDCP: still turn HDCP off on PS4/PS5.",
    "Capture sticks are usually USB 2 MJPG devices: 1080p30 or 720p60. Set capture.fps to 30 "
    "(or width/height to 1280x720) in config/device_config.json to match.",
]


def splitter_text() -> str:
    lines = [
        "HDMI splitter setup:",
        "  1. Console HDMI Out -> splitter In",
        "  2. Splitter Out 1 -> TV (you play on this)",
        "  3. Splitter Out 2 -> capture stick -> laptop USB",
    ]
    lines += [f"  - {item}" for item in CHECKLIST]
    return "\n".join(lines)


class SplitterDriver:
    """Splitters are passive: nothing to configure. Kept for older scripts."""

    requires_driver = False

    def checklist(self) -> List[str]:
        return list(CHECKLIST)

    def __str__(self) -> str:
        return splitter_text()
