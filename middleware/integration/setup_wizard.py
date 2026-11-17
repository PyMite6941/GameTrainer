"""
Guided first-time setup: `gametrainer --setup`.

Walks a new user through everything in order, with plain questions:

  1. this computer (Raspberry Pi / laptop / desktop): ports, power, packages
  2. the console and how to wire it (passthrough or monitor mode)
  3. finding the capture card and saving its index
  4. choosing a game, or creating a profile for a new one
  5. teaching it the players' colors (click + number key)
  6. a 10-second test that reports how well each player is tracked

Every step can be skipped and the wizard can be re-run at any time; it only
writes ./config/device_config.json and ./config/games/<game>.json.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

CONSOLES: List[Tuple[str, str]] = [
    ("switch", "Nintendo Switch"),
    ("ps5", "PlayStation 5"),
    ("ps4", "PlayStation 4"),
    ("xbox", "Xbox Series X|S"),
    ("xb1", "Xbox One"),
    ("generic", "Something else (PC, other console)"),
]


def _ask(prompt: str, default: str = "") -> str:
    try:
        ans = input(f"{prompt}{f' [{default}]' if default else ''}: ").strip()
    except EOFError:
        return default
    return ans or default


def _yes(prompt: str, default: bool = True) -> bool:
    ans = _ask(f"{prompt} ({'Y/n' if default else 'y/N'})").lower()
    return default if not ans else ans.startswith("y")


def _choose(prompt: str, options: Sequence[str], default: int = 1) -> int:
    for i, opt in enumerate(options, 1):
        print(f"    {i}. {opt}")
    while True:
        ans = _ask(prompt, str(default))
        if ans.isdigit() and 1 <= int(ans) <= len(options):
            return int(ans) - 1
        print(f"    Please type a number from 1 to {len(options)}.")


def _header(n: int, total: int, title: str) -> None:
    print(f"\n── Step {n}/{total}: {title} " + "─" * max(0, 50 - len(title)))


def print_guide() -> None:
    print("GameTrainer setup needs an interactive terminal. The same steps by hand:")
    print("  1. gametrainer --check                      (this computer: ports, power, packages)")
    print("  2. gametrainer --wiring switch              (or ps5, ps4, xbox)")
    print("  3. gametrainer --list-devices --save        (find the capture card)")
    print("  4. gametrainer --new-game \"My Game\" --kind fighter   (or use an existing profile)")
    print("  5. gametrainer <game> --calibrate           (click a player, press their number)")
    print("  6. gametrainer <game> --seconds 10 --preview")


def run_wizard(output: str = "./data", calibrate: Optional[Callable[[str], int]] = None) -> int:
    if not sys.stdin.isatty():
        print_guide()
        return 0

    from hardware_tools.adapters.hdmi_adapter import wiring_text
    from hardware_tools.adapters.usb_adapter import link_advice
    from hardware_tools.host import host_checks
    from middleware.capture.usb_capture import find_capture_card, list_devices
    from middleware.integration.system_integration import (
        GAME_KINDS, create_profile, list_profiles, save_device_index,
    )

    total = 6
    print("GameTrainer setup - about 5 minutes. Ctrl+C stops at any point; run it again to redo a step.")

    # 1. Host ----------------------------------------------------------------
    _header(1, total, "This computer")
    problems = 0
    for status, name, detail in host_checks():
        print(f"  [{status:4s}] {name}: {detail}")
        problems += status == "FAIL"
    if problems and not _yes("  There is a problem above. Continue anyway?", default=False):
        return 1

    # 2. Console and wiring --------------------------------------------------
    _header(2, total, "Your console")
    idx = _choose("  Which console?", [label for _, label in CONSOLES])
    console = CONSOLES[idx][0]
    print()
    print(wiring_text(console))
    mode = _choose("  How will you see the game while playing?", [
        "TV plugged into the capture card's HDMI Out (passthrough - no lag, recommended)",
        "TV plugged into this computer; GameTrainer shows the game (monitor mode)",
    ])
    monitor = mode == 1
    _ask("  Connect everything, turn the console on, then press Enter")

    # 3. Capture card ---------------------------------------------------------
    _header(3, total, "Capture card")
    card = None
    while True:
        print("  Looking for video devices...")
        devices = list_devices()
        for d in devices:
            print(f"    {d.describe()}")
        card = find_capture_card()
        if card:
            print(f"  Found it: index {card.index}.")
            if card.usb_speed_mbps is not None and not card.usb3:
                print("  " + link_advice(card))
            path = save_device_index(card.index)
            print(f"  Saved to {path}")
            break
        print("  No capture card is delivering a picture.")
        print("  Check: card's USB in a blue/SS port, console on, HDMI into the card's HDMI *In*.")
        if console in ("ps4", "ps5"):
            print("  PlayStation: HDCP must be off (see above).")
        if not _yes("  Try again?"):
            print("  Skipping - you can test with a recorded video or --synthetic, and run "
                  "`gametrainer --list-devices --save` later.")
            break

    # 4. Game --------------------------------------------------------------
    _header(4, total, "Your game")
    profiles = list_profiles()
    names = []
    for p in profiles:
        try:
            import json

            names.append(f"{json.loads(p.read_text()).get('name', p.stem)}  ({p.stem})")
        except Exception:
            names.append(p.stem)
    choice = _choose("  Which game?", names + ["A game that isn't listed - create it"], default=len(names) + 1)
    if choice < len(profiles):
        profile = profiles[choice]
    else:
        name = _ask("  Game name", "My Game")
        kinds = list(GAME_KINDS)
        kind = kinds[_choose("  What kind of game?", [GAME_KINDS[k] for k in kinds])]
        players = 1
        if kind != "any":
            ans = _ask("  How many players to track (1-8)", "2")
            players = int(ans) if ans.isdigit() else 2
        try:
            profile = create_profile(name, console=console, kind=kind, players=players)
        except FileExistsError:
            from middleware.integration.system_integration import resolve_profile, slugify

            profile = resolve_profile(slugify(name))
            print(f"  A profile with that name exists already - using {profile}")
        else:
            print(f"  Created {profile}")
    game = Path(profile).stem

    # 5. Colors ------------------------------------------------------------
    _header(5, total, "Teach it the players")
    import os

    has_display = sys.platform in ("win32", "darwin") or bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if card is None:
        print(f"  Skipped (no capture card). Later: gametrainer {game} --calibrate")
    elif not has_display:
        print("  This needs the computer's screen. On its desktop run:")
        print(f"    gametrainer {game} --calibrate")
    elif calibrate and _yes("  Start a match, then open the calibration window now?"):
        print("  In the window: click a player, then press their number (1 = p1, 2 = p2 ...).")
        print("  Space freezes the picture so you can click a moving player. q when done.")
        calibrate(game)
    else:
        print(f"  Later: gametrainer {game} --calibrate")

    # 6. Test --------------------------------------------------------------
    _header(6, total, "Quick test")
    play = f"gametrainer {game}{' --monitor' if monitor else ''} --build-replay --stats --view"
    if card is not None and _yes("  Track 10 seconds of gameplay to check it works?"):
        from middleware.integration.system_integration import run_session

        seen = {}
        frames = [0]

        def count(res):
            frames[0] += 1
            for d in res["detections"]:
                if d.get("x") is not None:
                    seen[d["player_id"]] = seen.get(d["player_id"], 0) + 1

        try:
            result = run_session(game, device=card.index, output=output, seconds=10, on_frame=count)
        except Exception as e:  # report and keep going: the wizard should never crash
            print(f"  Test failed: {e}")
        else:
            for w in result.warnings:
                print(f"  Warning: {w}")
            if frames[0] == 0:
                print("  No frames were tracked - check the capture card with `gametrainer --check`.")
            else:
                import json

                ents = json.loads(Path(profile).read_text()).get("entities", [])
                for e in ents:
                    pid = e.get("player_id") or e["name"]
                    pct = 100 * seen.get(pid, 0) / frames[0]
                    verdict = "good" if pct >= 80 else ("ok" if pct >= 40 else "poor - recalibrate this player")
                    print(f"    {pid}: seen in {pct:.0f}% of frames ({verdict})")
                print(f"  Replay of the test: {result.replay_path}")

    print("\nAll set. To play and review a match:")
    print(f"  {play}")
    print("Stop with Ctrl+C (or q on the monitor screen) when the match ends.")
    return 0
