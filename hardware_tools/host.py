"""
Host device: the computer the console plugs into.

GameTrainer runs on the *host*: a Raspberry Pi 4/5, a laptop, or a desktop. What
matters is that it has the right ports:

  * a USB 3 port for the capture card (USB 2 can't carry 1080p60)
  * a video output (HDMI, or micro-HDMI on a Pi) if the host drives the screen
    (monitor mode), or for viewing replays
  * on a Raspberry Pi, a full-power supply: an under-powered Pi browns out the
    USB ports and the capture card drops frames or disconnects

host_info() describes this machine; host_checks() feeds `gametrainer --check`.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REQUIREMENTS = {
    "usb": "a USB 3 port (5 Gb/s; blue or marked SS) for the capture card",
    "video": "an HDMI output for the screen (Raspberry Pi: micro-HDMI to HDMI cable) - needed for monitor mode and replays",
    "cpu": "any 64-bit CPU from the last ~8 years, or a Raspberry Pi 4/5; no GPU needed",
    "ram": "2 GB RAM minimum, 4 GB recommended",
    "os": "Linux (Raspberry Pi OS 64-bit, Ubuntu, ...), Windows 10/11, or macOS",
    "power": "Raspberry Pi: the official power supply (Pi 4: 5V 3A, Pi 5: 5V 5A)",
}


def pi_model() -> Optional[str]:
    """'Raspberry Pi 4 Model B Rev 1.4' on a Pi, else None."""
    for path in ("/proc/device-tree/model", "/sys/firmware/devicetree/base/model"):
        try:
            model = Path(path).read_bytes().decode(errors="ignore").strip("\x00 \n")
        except OSError:
            continue
        if "raspberry pi" in model.lower():
            return model
    return None


def ram_gb() -> Optional[float]:
    try:
        if hasattr(os, "sysconf") and "SC_PHYS_PAGES" in os.sysconf_names:
            return round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1e9, 1)
    except (ValueError, OSError):
        pass
    return None


def usb_root_speeds() -> List[int]:
    """Link speeds (Mb/s) of the USB root hubs on Linux: 480 = USB 2, 5000+ = USB 3."""
    speeds = []
    for hub in Path("/sys/bus/usb/devices").glob("usb*"):
        try:
            speeds.append(int(float((hub / "speed").read_text().strip())))
        except (OSError, ValueError):
            continue
    return speeds


def connected_displays() -> List[str]:
    """Connected video outputs on Linux (from DRM), e.g. ['HDMI-A-1']."""
    out = []
    for status in Path("/sys/class/drm").glob("card*-*/status"):
        try:
            if status.read_text().strip() == "connected":
                out.append(status.parent.name.split("-", 1)[1])
        except OSError:
            continue
    return sorted(out)


def pi_throttled() -> Optional[int]:
    """Raw `vcgencmd get_throttled` bits on a Raspberry Pi (0 = no power/heat problems)."""
    if not shutil.which("vcgencmd"):
        return None
    try:
        out = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=5).stdout
        return int(out.strip().split("=")[1], 16)
    except (OSError, subprocess.TimeoutExpired, IndexError, ValueError):
        return None


def host_info() -> Dict[str, object]:
    pi = pi_model()
    return {
        "device": pi or f"{platform.system()} computer",
        "is_raspberry_pi": pi is not None,
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "cpus": os.cpu_count(),
        "ram_gb": ram_gb(),
        "usb_root_speeds": usb_root_speeds() if sys.platform.startswith("linux") else None,
        "displays": connected_displays() if sys.platform.startswith("linux") else None,
    }


def host_checks() -> List[Tuple[str, str, str]]:
    """(status, name, detail) rows for the system check."""
    info = host_info()
    rows: List[Tuple[str, str, str]] = []
    rows.append(("INFO", "Host device", f"{info['device']}, {info['arch']}, {info['cpus']} CPU cores"
                 + (f", {info['ram_gb']} GB RAM" if info["ram_gb"] else "")))

    if info["arch"] and info["arch"].lower() not in ("x86_64", "amd64", "aarch64", "arm64"):
        rows.append(("WARN", "64-bit OS", f"{info['arch']} - use a 64-bit OS (Raspberry Pi OS 64-bit) for OpenCV wheels and speed"))
    if info["ram_gb"] is not None and info["ram_gb"] < 2:
        rows.append(("WARN", "Memory", f"{info['ram_gb']} GB - 2 GB is the minimum, 4 GB recommended"))

    speeds = info["usb_root_speeds"]
    if speeds is not None:
        if any(s >= 5000 for s in speeds):
            rows.append(("OK", "USB 3 ports", "this host has USB 3 - plug the capture card into a blue/SS port"))
        elif speeds:
            rows.append(("WARN", "USB 3 ports", "only USB 2 found - a capture card will be limited to ~1080p30/720p60 "
                         "(Raspberry Pi 3 and older have no USB 3; use a Pi 4/5 or a computer with USB 3)"))

    displays = info["displays"]
    if displays is not None:
        if displays:
            rows.append(("OK", "Screen output", "connected: " + ", ".join(displays)))
        elif Path("/sys/class/drm").exists():
            rows.append(("INFO", "Screen output", "no screen connected to this host - fine with a passthrough card; "
                         "monitor mode and the replay viewer need one"))

    if info["is_raspberry_pi"]:
        bits = pi_throttled()
        if bits is None:
            rows.append(("INFO", "Pi power", "vcgencmd not available - can't check for under-voltage"))
        elif bits & 0x1:
            rows.append(("FAIL", "Pi power", "under-voltage right now - use the official power supply; "
                         "the capture card will drop out"))
        elif bits & 0x10000:
            rows.append(("WARN", "Pi power", "under-voltage happened since boot - the power supply is too weak "
                         "for a capture card; use the official one"))
        elif bits & 0x40000 or bits & 0x4:
            rows.append(("WARN", "Pi temperature", "the Pi throttled from heat - add a heatsink or fan"))
        else:
            rows.append(("OK", "Pi power", "no under-voltage or throttling since boot"))
    return rows


def requirements_text() -> str:
    return "Host device requirements:\n" + "\n".join(f"  - {v}" for v in REQUIREMENTS.values())
