"""
System check: is this machine ready to track games?

    gametrainer --check          (or: python check_system.py)

Each check reports OK, WARN (works, but something is worth fixing), FAIL
(tracking won't work until it's fixed) or INFO. The exit code is 1 when any
check fails.
"""

from __future__ import annotations

import importlib
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional


@dataclass
class Check:
    status: str  # OK / WARN / FAIL / INFO
    name: str
    detail: str = ""


def _module_version(name: str) -> Optional[str]:
    try:
        mod = importlib.import_module(name)
    except Exception:
        return None
    return str(getattr(mod, "__version__", getattr(mod, "version", "installed")))


def run_checks(probe_devices: bool = True, data_dir: str = "./data") -> List[Check]:
    out: List[Check] = []
    add = lambda *a: out.append(Check(*a))  # noqa: E731

    # Python and packages
    v = sys.version_info
    add("OK" if v >= (3, 9) else "FAIL", "Python", f"{v.major}.{v.minor}.{v.micro}" + ("" if v >= (3, 9) else " (3.9+ required)"))
    for mod, label, required in (
        ("numpy", "numpy", True),
        ("cv2", "OpenCV", True),
        ("pygame", "pygame (replay viewer)", True),
        ("pandas", "pandas (player profiler)", False),
        ("pytesseract", "pytesseract (HUD OCR, optional)", False),
    ):
        ver = _module_version(mod)
        if ver:
            add("OK", label, ver)
        else:
            add("FAIL" if required else ("INFO" if "optional" in label else "WARN"), label,
                f"not installed - pip install {'opencv-python' if mod == 'cv2' else mod}")

    if _module_version("cv2") is None:
        return out  # nothing below works without OpenCV

    from middleware.analysis.frame_processor import TESSERACT_AVAILABLE, GameProfile
    from middleware.capture.hdmi_capture import camera_backends
    from middleware.integration.system_integration import device_config_path, list_profiles, load_device_config

    backends = camera_backends()
    add("OK" if backends else "WARN", "OpenCV camera backends", ", ".join(backends) or "none reported")
    if _module_version("pytesseract"):
        add("OK" if TESSERACT_AVAILABLE else "INFO", "Tesseract binary",
            "found" if TESSERACT_AVAILABLE else "not found - install tesseract-ocr to read HUD text")

    # Config
    path = device_config_path()
    warnings: List[str] = []
    cfg = load_device_config(warn=warnings.append)
    if path is None:
        add("INFO", "Device config", "none found - using defaults (device 0, 1080p60 MJPG)")
    elif warnings:
        add("FAIL", "Device config", warnings[0])
    else:
        cap = cfg["capture"]
        add("OK", "Device config", f"{path} - device {cfg['device'].get('index')}, "
            f"{cap.get('width')}x{cap.get('height')}@{cap.get('fps')} {cap.get('fourcc') or 'default format'}")

    profiles = list_profiles()
    if not profiles:
        add("FAIL", "Game profiles", "none found in config/games/")
    for p in profiles:
        try:
            prof = GameProfile(p)
        except (ValueError, json.JSONDecodeError, OSError) as e:
            add("FAIL", f"Profile {p.stem}", str(e))
            continue
        warns = [w[9:] for w in prof.problems if w.startswith("warning:")]
        warns += [f"template image missing: {Path(m).name}" for m in prof.missing_templates]
        add("WARN" if warns else "OK", f"Profile {p.stem}", "; ".join(warns) or prof.name)

    # Storage
    data = Path(data_dir)
    try:
        data.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=data):
            pass
        free_gb = shutil.disk_usage(data).free / 1e9
        add("OK" if free_gb >= 1 else "WARN", "Data folder", f"{data.resolve()} writable, {free_gb:.1f} GB free")
    except OSError as e:
        add("FAIL", "Data folder", f"{data.resolve()} not writable: {e}")

    # Linux permissions and tools
    if sys.platform.startswith("linux"):
        try:
            import grp

            gid = grp.getgrnam("video").gr_gid
            in_group = gid in os.getgroups() or os.geteuid() == 0
            add("OK" if in_group else "WARN", "Permission to open cameras",
                "user is in the 'video' group" if in_group else
                "user is not in the 'video' group: run  sudo usermod -aG video $USER  then log out and in")
        except (KeyError, ImportError):
            pass
        add("OK" if shutil.which("v4l2-ctl") else "INFO", "v4l2-ctl",
            "found" if shutil.which("v4l2-ctl") else "not installed (optional) - sudo apt install v4l-utils lists card modes")

    has_display = sys.platform in ("win32", "darwin") or bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    add("OK" if has_display else "INFO", "Display", "available for the replay viewer and --preview" if has_display
        else "none - tracking works; open replays on a machine with a screen")

    # Capture hardware
    if probe_devices:
        from hardware_tools.adapters.usb_adapter import link_advice
        from hardware_tools.drivers.capture_card_driver import list_modes, best_mode
        from middleware.capture.usb_capture import find_capture_card, list_devices

        devices = list_devices()
        if not devices:
            add("WARN", "Capture card", "none detected - plug the card into USB and connect the console (see docs/HARDWARE_SETUP.md)")
        else:
            for d in devices:
                add("INFO", "Video device", d.describe())
            card = find_capture_card()
            if card is None:
                add("WARN", "Capture card", "devices found but none delivers frames - is the console on and connected?")
            else:
                configured = int(cfg["device"].get("index", 0))
                add("OK" if card.index == configured else "WARN", "Capture card",
                    f"index {card.index}" + ("" if card.index == configured else
                                            f" but device_config.json uses {configured}: run  gametrainer --list-devices --save"))
                if card.usb_speed_mbps is not None:
                    add("OK" if card.usb3 else "WARN", "USB link", link_advice(card))
                best = best_mode(list_modes(card.index))
                if best:
                    cap = cfg["capture"]
                    same = (cap.get("width"), cap.get("height"), (cap.get("fourcc") or "")) == (best.width, best.height, best.fourcc)
                    add("OK" if same else "INFO", "Capture mode",
                        f"best available {best}" + ("" if same else f"; set capture to {json.dumps(best.as_config())}"))
    return out


def print_report(checks: List[Check], write: Callable[[str], None] = print) -> int:
    width = max(len(c.name) for c in checks) if checks else 10
    for c in checks:
        write(f"  [{c.status:4s}] {c.name:{width}s}  {c.detail}")
    fails = sum(c.status == "FAIL" for c in checks)
    warns = sum(c.status == "WARN" for c in checks)
    write("")
    if fails:
        write(f"{fails} problem(s) must be fixed before tracking.")
    elif warns:
        write(f"Ready to track, with {warns} warning(s) worth fixing.")
    else:
        write("Ready to track.")
    return 1 if fails else 0


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    print("GameTrainer system check")
    return print_report(run_checks(probe_devices="--no-devices" not in argv))


if __name__ == "__main__":
    raise SystemExit(main())
