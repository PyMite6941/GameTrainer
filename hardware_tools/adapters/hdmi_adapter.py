"""
HDMI adapter: how each console connects to the capture chain, and what to set.

The host is the computer GameTrainer runs on: a Raspberry Pi 4/5, a laptop, or a
desktop with a USB 3 port. Two ways to wire it:

  A. Passthrough (lowest lag, recommended for competitive play)
     console HDMI Out -> capture card HDMI In
     capture card HDMI Out -> TV / monitor
     capture card USB -> host USB 3 port      (the host records data points)

  B. Monitor mode (host drives the screen: `gametrainer <game> --monitor`)
     console HDMI Out -> capture card HDMI In
     capture card USB -> host USB 3 port
     host HDMI Out -> TV / monitor            (~1-3 frames of added lag)

`console_setup("ps5")` returns the steps and settings for one console;
`wiring_text(console)` renders them for the terminal.
"""

from __future__ import annotations

from typing import Dict, List

CHAIN = [
    "Console HDMI Out -> capture card HDMI In",
    "Capture card USB -> host USB 3 port (Raspberry Pi 4/5, laptop or desktop; blue port or marked SS)",
    "Screen, either:  A) capture card HDMI Out -> TV (passthrough, no added lag), or",
    "                 B) host HDMI Out -> TV and run with --monitor (the host shows the game; slight lag)",
]

CONSOLES: Dict[str, Dict[str, object]] = {
    "nintendo_switch_2": {
        "name": "Nintendo Switch 2",
        "family": "nintendo",
        "hdcp": "Games aren't HDCP-protected; no setting needed.",
        "output": "System Settings > TV Output > TV Resolution: 1080p, and turn 120 Hz output off (most cards capture 60 Hz).",
        "steps": [
            "Put the Switch 2 in its dock; handheld mode has no HDMI output.",
            "Connect the dock's HDMI Out to the capture card's HDMI In.",
            "Original Switch games (Smash, Mario Kart 8 Deluxe ...) work the same on Switch 2.",
        ],
    },
    "nintendo_switch": {
        "name": "Nintendo Switch / Switch OLED",
        "family": "nintendo",
        "hdcp": "No setting needed: the Switch doesn't encrypt game output.",
        "output": "System Settings > TV Output > TV Resolution: 1080p.",
        "steps": [
            "Put the Switch in its dock; handheld mode has no HDMI output.",
            "Connect the dock's HDMI Out (not the TV directly) to the capture card's HDMI In.",
            "The Switch Lite has no video output and can't be tracked.",
        ],
    },
    "wii_u": {
        "name": "Wii U",
        "family": "nintendo",
        "hdcp": "Games aren't HDCP-protected; no setting needed.",
        "output": "System Settings > TV > TV Resolution: 1080p (games render at 720p; that's fine).",
        "steps": ["Only the TV picture is captured, not the GamePad screen."],
    },
    "wii": {
        "name": "Wii",
        "family": "nintendo",
        "via": "Console AV port -> Wii-to-HDMI adapter -> capture card HDMI In",
        "hdcp": "Analog output, no HDCP.",
        "output": "Wii Settings > Screen > TV Resolution: EDTV/HDTV (480p), widescreen 16:9.",
        "steps": [
            "The Wii has no HDMI port: use a Wii-to-HDMI adapter (480p) into the capture card's HDMI In.",
            "Most adapters output 480p (or 720p); GameTrainer tracks that size as-is, which is light on the CPU.",
        ],
    },
    "retro": {
        "name": "Retro consoles (GameCube, N64, SNES, PS1/PS2, Dreamcast ...)",
        "family": "retro",
        "via": "Console AV out -> analog-to-HDMI adapter or upscaler -> capture card HDMI In",
        "hdcp": "Analog output, no HDCP.",
        "output": "Use the console's best cable (component or RGB) where it has one.",
        "steps": [
            "These consoles have no HDMI: put an analog-to-HDMI adapter or line-doubler/upscaler "
            "between the console and the capture card's HDMI In.",
            "An upscaler with a fixed 720p/1080p output gives the steadiest picture to track.",
        ],
    },
    "playstation_5": {
        "name": "PlayStation 5 / PS5 Pro",
        "family": "playstation",
        "hdcp": "Settings > System > HDMI > Enable HDCP: OFF (otherwise the card gets a black picture).",
        "output": "Settings > Screen and Video > Video Output > Resolution: 1080p (most cards pass through 4K but capture 1080p).",
        "steps": ["Turning HDCP off disables streaming apps (Netflix etc.) until you turn it back on."],
    },
    "playstation_4": {
        "name": "PlayStation 4 / PS4 Pro",
        "family": "playstation",
        "hdcp": "Settings > System > Enable HDCP: OFF.",
        "output": "Settings > Sound and Screen > Video Output Settings > Resolution: 1080p.",
        "steps": [],
    },
    "playstation_3": {
        "name": "PlayStation 3",
        "family": "playstation",
        "via": "Console component (YPbPr) cable -> component-to-HDMI converter -> capture card HDMI In",
        "hdcp": "The PS3 always uses HDCP on HDMI and it can't be turned off.",
        "output": "Use the component (YPbPr) AV cable at 720p instead of HDMI.",
        "steps": [
            "Connect the component cable to a capture device with component input, or to a "
            "component-to-HDMI converter into the capture card's HDMI In.",
        ],
    },
    "xbox_series": {
        "name": "Xbox Series X|S",
        "family": "xbox",
        "hdcp": "Games aren't HDCP-protected; no setting needed.",
        "output": "Settings > General > TV & display options > Resolution: 1080p, refresh 60 Hz.",
        "steps": ["If the picture is black, set Video modes > Allow 4K and Allow HDR off."],
    },
    "xbox_one": {
        "name": "Xbox One / One S / One X",
        "family": "xbox",
        "hdcp": "Games aren't HDCP-protected; no setting needed.",
        "output": "Settings > Display & sound > Video output > Resolution: 1080p.",
        "steps": [],
    },
    "xbox_360": {
        "name": "Xbox 360",
        "family": "xbox",
        "hdcp": "Games aren't HDCP-protected over HDMI; no setting needed.",
        "output": "System Settings > Console Settings > Display > HDTV Settings: 1080p (or 720p).",
        "steps": ["Early models without an HDMI port need the component cable and a component-to-HDMI converter."],
    },
    "steam_deck": {
        "name": "Steam Deck and PC handhelds (ROG Ally, Legion Go ...)",
        "family": "pc",
        "hdcp": "Games aren't HDCP-protected; no setting needed.",
        "output": "Set the external display to 1920x1080 at 60 Hz.",
        "steps": ["Use a dock or a USB-C-to-HDMI adapter into the capture card's HDMI In."],
    },
    "pc": {
        "name": "Gaming PC",
        "family": "pc",
        "hdcp": "Games aren't HDCP-protected; no setting needed.",
        "output": "Mirror or extend to the capture card at 1920x1080, 60 Hz.",
        "steps": ["Use a second HDMI/DisplayPort output (or an HDMI splitter) so your own monitor stays native."],
    },
    "generic": {
        "name": "Any HDMI console or PC",
        "family": "other",
        "hdcp": "If the capture is black, the source is sending HDCP: turn it off in the console's settings.",
        "output": "Set the console's output to 1080p at 60 Hz.",
        "steps": [],
    },
}

ALIASES = {
    "switch": "nintendo_switch", "ns": "nintendo_switch", "switch_oled": "nintendo_switch",
    "switch2": "nintendo_switch_2", "switch_2": "nintendo_switch_2", "ns2": "nintendo_switch_2",
    "wiiu": "wii_u",
    "gamecube": "retro", "gc": "retro", "n64": "retro", "snes": "retro", "ps1": "retro", "ps2": "retro",
    "playstation_2": "retro", "dreamcast": "retro",
    "ps5": "playstation_5", "ps5_pro": "playstation_5", "ps4": "playstation_4", "ps3": "playstation_3",
    "xbox": "xbox_series", "xsx": "xbox_series", "xss": "xbox_series", "xbox_series_x": "xbox_series",
    "xbox_series_s": "xbox_series", "xb1": "xbox_one", "x360": "xbox_360", "360": "xbox_360",
    "deck": "steam_deck", "steamdeck": "steam_deck", "rog_ally": "steam_deck", "legion_go": "steam_deck",
    "computer": "pc",
}


def list_consoles() -> List[Dict[str, object]]:
    """Every supported console with its key and the short names it answers to."""
    out = []
    for key, info in CONSOLES.items():
        short = sorted(a for a, k in ALIASES.items() if k == key)
        if len(key) <= 8 and key not in short:
            short.insert(0, key)
        out.append({"key": key, "short_names": short, **info})
    return out


def console_key(console: str) -> str:
    key = (console or "generic").lower().replace(" ", "_").replace("-", "_")
    return ALIASES.get(key, key if key in CONSOLES else "generic")


def console_setup(console: str) -> Dict[str, object]:
    info = dict(CONSOLES[console_key(console)])
    info["chain"] = list(CHAIN)
    if info.get("via"):  # no usable HDMI out: an adapter feeds the capture card
        info["chain"][0] = str(info["via"])
    return info


def wiring_text(console: str = "generic") -> str:
    info = console_setup(console)
    lines: List[str] = [f"{info['name']}:"]
    chain = info["chain"]
    lines += [f"  {i}. {step}" for i, step in enumerate(chain[:3], 1)]
    lines += [f"     {step.strip()}" for step in chain[3:]]
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
