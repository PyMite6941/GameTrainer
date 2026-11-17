#!/usr/bin/env python3
"""
GameTrainer installer: set up the capture middleware on this machine.

    python3 install_middleware.py              # venv in .venv, install, check, verify
    python3 install_middleware.py --ocr        # also HUD text reading (pytesseract)
    python3 install_middleware.py --binary     # also build dist/gametrainer
    python3 install_middleware.py --yes        # don't ask before saving the capture card index

What it does (and never does):
  * creates .venv (unless --no-venv) and installs GameTrainer into it with pip
  * creates data/ and, only if missing, config/device_config.json
  * runs the system check and, if a capture card is connected, offers to save its index
  * runs the 50-check end-to-end verification (skip with --skip-verify)
  * never overwrites existing files, never uses sudo - it prints the system
    commands (apt, usermod) for you to run instead
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

REPO = Path(__file__).resolve().parent
MIN_PYTHON = (3, 9)
DEFAULT_DEVICE_CONFIG = {
    "device": {"index": 0, "note": "Video index of the capture card. Find it with: gametrainer --list-devices --save"},
    "capture": {
        "width": 1920, "height": 1080, "fps": 60, "fourcc": "MJPG",
        "downscale_width": 1280, "process_every_n_frames": 2, "detect_scale": 0.5,
    },
}


def step(msg: str) -> None:
    print(f"\n==> {msg}", flush=True)


def run(cmd: List[str], check: bool = True, **kw) -> subprocess.CompletedProcess:
    """Run a command given as a list (no shell, so version specifiers can't become redirects)."""
    print("    $ " + " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=check, cwd=REPO, **kw)


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def ensure_python(args) -> Path:
    if sys.version_info < MIN_PYTHON:
        sys.exit(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required; this is {platform.python_version()}.")
    print(f"    Python {platform.python_version()} on {platform.system()} {platform.machine()}")
    if args.no_venv:
        return Path(sys.executable)
    venv = (REPO / args.venv).resolve()
    py = venv_python(venv)
    if py.exists():
        print(f"    using existing virtual environment {venv}")
    else:
        try:
            run([sys.executable, "-m", "venv", str(venv)])
        except subprocess.CalledProcessError:
            sys.exit("Could not create a virtual environment. On Debian/Ubuntu/Raspberry Pi OS run:\n"
                     "    sudo apt install python3-venv\nthen run this installer again.")
    return py


def install_packages(py: Path, args) -> None:
    run([str(py), "-m", "pip", "install", "--upgrade", "pip"], check=False)
    target = ".[ocr]" if args.ocr else "."
    cmd = [str(py), "-m", "pip", "install"] + (["-e"] if not args.no_editable else []) + [target]
    result = run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        err = (result.stderr or "") + (result.stdout or "")
        if "externally-managed-environment" in err:
            sys.exit("This Python is managed by the OS (PEP 668). Run the installer without --no-venv "
                     "so GameTrainer installs into its own .venv.")
        print(err[-2000:])
        sys.exit("pip install failed (see above).")
    print("    installed GameTrainer and its dependencies")


def prepare_files() -> None:
    for d in ("data", "data/replays"):
        (REPO / d).mkdir(parents=True, exist_ok=True)
    cfg = REPO / "config" / "device_config.json"
    if cfg.exists():
        print(f"    kept existing {cfg.relative_to(REPO)}")
    else:
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text(json.dumps(DEFAULT_DEVICE_CONFIG, indent=2) + "\n")
        print(f"    created {cfg.relative_to(REPO)}")


def system_hints(args) -> List[str]:
    hints: List[str] = []
    if sys.platform.startswith("linux"):
        try:
            import grp

            if grp.getgrnam("video").gr_gid not in os.getgroups() and os.geteuid() != 0:
                hints.append("sudo usermod -aG video $USER    # then log out and back in (lets you open the capture card)")
        except (KeyError, ImportError):
            pass
        apt = []
        if not shutil.which("v4l2-ctl"):
            apt.append("v4l-utils")
        if args.ocr and not shutil.which("tesseract"):
            apt.append("tesseract-ocr")
        if apt and shutil.which("apt"):
            hints.append("sudo apt install " + " ".join(apt))
    elif sys.platform == "darwin" and args.ocr and not shutil.which("tesseract"):
        hints.append("brew install tesseract")
    elif os.name == "nt" and args.ocr and not shutil.which("tesseract"):
        hints.append("Install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki and add it to PATH")
    return hints


def detect_card(py: Path, args) -> None:
    probe = run([str(py), "-c",
                 "import json,sys; sys.path.insert(0,'.');"
                 "from middleware.capture.usb_capture import find_capture_card as f; c=f();"
                 "print(json.dumps(c.to_dict() if c else None))"],
                check=False, capture_output=True, text=True)
    try:
        card = json.loads(probe.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        card = None
    if not card:
        print("    no capture card delivering frames right now - connect it later and run:")
        print("      gametrainer --list-devices --save")
        return
    print(f"    found a capture card at index {card['index']} ({card['width']}x{card['height']})")
    save = args.yes or (sys.stdin.isatty() and input("    Save this index to config/device_config.json? [Y/n] ").strip().lower() in ("", "y", "yes"))
    if save:
        run([str(py), "track_game.py", "--list-devices", "--save"], check=False)


def main() -> int:
    p = argparse.ArgumentParser(description="Install the GameTrainer capture middleware.")
    p.add_argument("--venv", default=".venv", help="Virtual environment folder (default .venv)")
    p.add_argument("--no-venv", action="store_true", help="Install into the current Python instead of a venv")
    p.add_argument("--no-editable", action="store_true", help="Copy the code into the environment instead of linking it")
    p.add_argument("--ocr", action="store_true", help="Also install HUD text reading (pytesseract)")
    p.add_argument("--binary", action="store_true", help="Also build the one-file desktop binary")
    p.add_argument("--skip-verify", action="store_true", help="Skip the end-to-end verification")
    p.add_argument("--yes", action="store_true", help="Save a detected capture card index without asking")
    args = p.parse_args()

    print("GameTrainer middleware installer")
    step("Python environment")
    py = ensure_python(args)
    step("Installing GameTrainer")
    install_packages(py, args)
    step("Data and config folders")
    prepare_files()
    step("System check")
    run([str(py), "check_system.py", "--no-devices"], check=False)
    step("Capture card")
    detect_card(py, args)

    failed = False
    if not args.skip_verify:
        step("End-to-end verification (no hardware needed, about a minute)")
        failed = run([str(py), "verify_tracker.py"], check=False).returncode != 0
    if args.binary:
        step("Building the desktop binary")
        if os.name == "nt":
            run([str(py), "-m", "pip", "install", "pyinstaller"], check=False)
            failed |= run([str(py), "-m", "PyInstaller", "gametrainer.spec", "--clean", "--noconfirm"], check=False).returncode != 0
        else:
            failed |= run(["bash", "build_binary.sh"], check=False).returncode != 0

    hints = system_hints(args)
    if hints:
        step("Run these system commands yourself (they need admin rights)")
        for h in hints:
            print(f"    {h}")

    step("Done" if not failed else "Finished with problems (see above)")
    activate = (Path(args.venv) / ("Scripts\\activate" if os.name == "nt" else "bin/activate")) if not args.no_venv else None
    if activate:
        print(f"    Activate the environment:  {'' if os.name == 'nt' else 'source '}{activate}")
    print("    Connect a console:          gametrainer --wiring switch   (or ps5, ps4, xbox)")
    print("    Find the capture card:      gametrainer --list-devices --save")
    print("    Tune player colors:         gametrainer smash --calibrate")
    print("    Play and review:            gametrainer smash --build-replay --view")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
