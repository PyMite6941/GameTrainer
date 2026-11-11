"""
HDMI adapter: how each console connects to the capture chain, and what to set.

    console HDMI Out -> capture card HDMI In
    capture card HDMI Out -> TV            (passthrough: the TV is your monitor)
    capture card USB -> laptop USB 3 port  (the laptop records data points)

`console_setup("ps5")` returns the steps and settings for one console;
`wiring_text(console)` renders them for the terminal.
"""

from __future__ import annotations

from typing import Dict, List

CHAIN = [
    "Console HDMI Out -> capture card HDMI In",
    "Capture card HDMI Out -> TV (passthrough: you play on the TV with no added lag)",
    "Capture card USB -> laptop USB 3 port (blue port, or marked SS)",
]

CONSOLES: Dict[str, Dict[str, object]] = {
    "nintendo_switch": {
        "name": "Nintendo Switch / Switch OLED",
        "hdcp": "No setting needed: the Switch doesn't encrypt game output.",
        "output": "System Settings > TV Output > TV Resolution: 1080p.",
        "steps": [
            "Put the Switch in its dock; handheld mode has no HDMI output.",
            "Connect the dock's HDMI Out (not the TV directly) to the capture card's HDMI In.",
        ],
    },
    "playstation_5": {
        "name": "PlayStation 5",
        "hdcp": "Settings > System > HDMI > Enable HDCP: OFF (otherwise the card gets a black picture).",
        "output": "Settings > Screen and Video > Video Output > Resolution: 1080p (most cards pass through 4K but capture 1080p).",
        "steps": ["Turning HDCP off disables streaming apps (Netflix etc.) until you turn it back on."],
    },
    "playstation_4": {
        "name": "PlayStation 4 / PS4 Pro",
        "hdcp": "Settings > System > Enable HDCP: OFF.",
        "output": "Settings > Sound and Screen > Video Output Settings > Resolution: 1080p.",
        "steps": [],
    },
    "xbox_series": {
        "name": "Xbox Series X|S",
        "hdcp": "Games aren't HDCP-protected; no setting needed.",
        "output": "Settings > General > TV & display options > Resolution: 1080p, refresh 60 Hz.",
        "steps": ["If the picture is black, set Video modes > Allow 4K and Allow HDR off."],
    },
    "xbox_one": {
        "name": "Xbox One",
        "hdcp": "Games aren't HDCP-protected; no setting needed.",
        "output": "Settings > Display & sound > Video output > Resolution: 1080p.",
        "steps": [],
    },
    "generic": {
        "name": "Any HDMI console or PC",
        "hdcp": "If the capture is black, the source is sending HDCP: turn it off in the console's settings.",
        "output": "Set the console's output to 1080p at 60 Hz.",
        "steps": [],
    },
}

ALIASES = {
    "switch": "nintendo_switch", "ns": "nintendo_switch",
    "ps5": "playstation_5", "ps4": "playstation_4",
    "xbox": "xbox_series", "xsx": "xbox_series", "xss": "xbox_series", "xbox_series_x": "xbox_series",
    "xb1": "xbox_one",
}


def console_key(console: str) -> str:
    key = (console or "generic").lower().replace(" ", "_").replace("-", "_")
    return ALIASES.get(key, key if key in CONSOLES else "generic")


def console_setup(console: str) -> Dict[str, object]:
    info = dict(CONSOLES[console_key(console)])
    info["chain"] = list(CHAIN)
    return info


def wiring_text(console: str = "generic") -> str:
    info = console_setup(console)
    lines: List[str] = [f"{info['name']}:"]
    lines += [f"  {i}. {step}" for i, step in enumerate(info["chain"], 1)]
    for extra in info["steps"]:
        lines.append(f"  - {extra}")
    lines.append(f"  - HDCP: {info['hdcp']}")
    lines.append(f"  - Output: {info['output']}")
    return "\n".join(lines)


class HdmiAdapter:
    """Kept for older scripts: wiring info for a console."""

    def __init__(self, console: str = "generic"):
        self.console = console_key(console)

    def setup(self) -> Dict[str, object]:
        return console_setup(self.console)

    def __str__(self) -> str:
        return wiring_text(self.console)
