#!/usr/bin/env python3
"""
GameTrainer - CPU-only game tracker for any console game (Leetify model).

Capture:
    Console HDMI Out -> capture card HDMI In; card HDMI Out -> TV (passthrough,
    the TV stays your monitor); card USB -> laptop. The card is a UVC camera.

    After the game, `--build-replay` rebuilds the match from data points (no
    video) with Leetify-style stats, and `gametrainer <replay.json>` plays it.

Setup:
    gametrainer --check                   is this machine ready?
    gametrainer --wiring ps5              how to connect a console
    gametrainer --list-devices --save     find the capture card and remember it
    gametrainer smash --calibrate         click players to get their colors

Play:
    gametrainer smash --build-replay --view
    gametrainer --build-replay --stats    latest session's replay + scoreboard
    gametrainer ./data/replays/replay.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional, Union

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")  # keep OpenCV/FFmpeg probe noise out of the output
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

# Bundled files: the PyInstaller unpack dir when frozen, else the repo checkout.
APP_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
sys.path.insert(0, str(APP_DIR))

from middleware.integration.system_integration import (  # noqa: E402
    list_profiles,
    load_device_config,
    resolve_profile,
    save_device_index,
    user_dir,
)

__version__ = "1.2.0"
__all__ = ["main", "list_profiles", "resolve_profile", "load_device_config", "is_replay_file", "user_dir"]


def is_replay_file(path: str) -> bool:
    """A replay.json has a top-level "timeline"; a game profile does not."""
    if not path.lower().endswith(".json"):
        return False
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(data, dict) and "timeline" in data


def has_display() -> bool:
    if sys.platform.startswith("linux"):
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return True


def parse_device(value: Optional[str], cfg: dict) -> Union[int, str]:
    if value is None:
        return int(cfg["device"].get("index", 0))
    try:
        return int(value)
    except ValueError:
        return value


# --------------------------------------------------------------------- setup
def cmd_list_devices(save: bool) -> int:
    from middleware.capture.usb_capture import find_capture_card, list_devices

    print("Video devices (a capture card usually reports 1920x1080 or 1280x720):")
    devices = list_devices()
    for d in devices:
        print(f"  {d.describe()}")
    if not devices:
        print("  none found - check the capture card's USB cable and that the console is on.")
        return 1
    card = find_capture_card()
    if card is None:
        print("No device is delivering frames. Is the console on and connected to the card's HDMI In?")
        return 1
    print(f"\nMost likely capture card: index {card.index}")
    if save:
        path = save_device_index(card.index)
        print(f"Saved device.index = {card.index} to {path}")
    else:
        print("Save it with: gametrainer --list-devices --save   (or pass --device N)")
    return 0


def cmd_wiring(console: str) -> int:
    from hardware_tools.adapters.hdmi_adapter import wiring_text
    from hardware_tools.drivers.splitter_driver import splitter_text

    print(wiring_text(console))
    print("\nNo HDMI Out on your capture device?\n" + splitter_text())
    return 0


def load_image_or_frame(args, cfg) -> Optional["object"]:
    """A working-size frame from --image, or one grabbed from the capture device."""
    import cv2

    from middleware.capture.hdmi_capture import HdmiCapture

    if args.image:
        img = cv2.imread(args.image)
        if img is None:
            print(f"Can't read image {args.image}")
            return None
        if img.shape[1] > 1280:
            s = 1280 / img.shape[1]
            img = cv2.resize(img, (1280, int(img.shape[0] * s)), interpolation=cv2.INTER_AREA)
        return img
    cap = HdmiCapture.from_config(parse_device(args.device, cfg), cfg["capture"])
    try:
        cap.open()
    except RuntimeError as e:
        print(f"Capture error: {e}. Find the card with: gametrainer --list-devices")
        return None
    frame = None
    for _ in range(10):  # let the card's format settle; keep the last good frame
        f = cap.read()
        if f is not None:
            frame = f
    cap.close()
    if frame is None:
        print("The capture device opened but delivered no picture.")
    return frame


def cmd_pick(args, cfg) -> int:
    from middleware.analysis.frame_processor import sample_color

    frame = load_image_or_frame(args, cfg)
    if frame is None:
        return 1
    try:
        x, y = (int(v) for v in args.pick.split(","))
    except ValueError:
        print("--pick takes X,Y in working-frame pixels, e.g. --pick 640,360")
        return 1
    h, w = frame.shape[:2]
    if not (0 <= x < w and 0 <= y < h):
        print(f"({x}, {y}) is outside the {w}x{h} frame")
        return 1
    c = sample_color(frame, x, y)
    print(f"At ({x}, {y}): {c['color_name']}  hue {c['hue']}  saturation {c['saturation']}  brightness {c['brightness']}")
    print(f'Profile entity: "color_bgr": {c["color_bgr"]}, "hue_tolerance": 12')
    return 0


def cmd_calibrate(args, cfg) -> int:
    """Click on players in a live (or still) frame to read their colors."""
    import cv2

    from middleware.analysis.frame_processor import FrameProcessor, GameProfile, sample_color
    from middleware.capture.hdmi_capture import HdmiCapture

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    snapshot = out_dir / "calibration.png"
    profile = GameProfile(resolve_profile(args.target)) if args.target else None

    if not has_display():
        frame = load_image_or_frame(args, cfg)
        if frame is None:
            return 1
        cv2.imwrite(str(snapshot), frame)
        print(f"No display: saved a working-size frame to {snapshot}.")
        print("Open it in an image viewer, note a player's pixel position, then run:")
        print(f"  gametrainer --pick X,Y --image {snapshot}")
        return 0

    cap = None
    still = None
    if args.image:
        still = load_image_or_frame(args, cfg)
        if still is None:
            return 1
    else:
        cap = HdmiCapture.from_config(parse_device(args.device, cfg), cfg["capture"])
        try:
            cap.open()
        except RuntimeError as e:
            print(f"Capture error: {e}. Find the card with: gametrainer --list-devices")
            return 1

    processor = FrameProcessor(profile) if profile else None
    current = {"frame": still}
    picks: List[dict] = []

    def on_click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and current["frame"] is not None:
            c = sample_color(current["frame"], x, y)
            picks.append({"x": x, "y": y, **c})
            print(f"  ({x:4d},{y:4d}) {c['color_name']:7s} \"color_bgr\": {c['color_bgr']}   hue {c['hue']}")

    win = "GameTrainer calibrate - click players, s = save frame, q = quit"
    cv2.namedWindow(win)
    cv2.setMouseCallback(win, on_click)
    print("Click on each player's main color. Colors print here as profile JSON.")
    if profile:
        print(f"Circles show what '{profile.name}' currently detects.")
    try:
        while True:
            if cap is not None:
                f = cap.read()
                if f is None:
                    print("Capture stopped delivering frames.")
                    break
                current["frame"] = f
            frame = current["frame"].copy()
            if processor:
                for d in processor.process(current["frame"])["detections"]:
                    cv2.circle(frame, (d["x"], d["y"]), 18, (255, 255, 255), 2)
                    cv2.putText(frame, d["player_id"], (d["x"] + 20, d["y"]), cv2.FONT_HERSHEY_SIMPLEX,
                                0.5, (255, 255, 255), 1, cv2.LINE_AA)
            for p in picks[-8:]:
                cv2.drawMarker(frame, (p["x"], p["y"]), (0, 255, 255), cv2.MARKER_CROSS, 14, 2)
            cv2.imshow(win, frame)
            key = cv2.waitKey(30 if cap else 50) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("s"):
                cv2.imwrite(str(snapshot), current["frame"])
                print(f"  saved {snapshot}")
    finally:
        if cap:
            cap.close()
        cv2.destroyAllWindows()
    return 0


# ------------------------------------------------------------------ replays
def open_viewer(path: str) -> int:
    if not has_display():
        print(f"No display available. Copy {path} to a computer with a screen and open it there.")
        return 1
    try:
        from middleware.simulation.replay_viewer import ReplayViewer
    except ImportError as e:
        print(f"Replay viewer unavailable ({e}). Install pygame: pip install pygame")
        return 1
    ReplayViewer(path).run()
    return 0


def print_stats(replay_path: str) -> None:
    from middleware.analysis.feature_extractor import extract_features, format_stats

    with open(replay_path) as f:
        replay = json.load(f)
    stats = replay.get("stats") or extract_features(replay)
    print(format_stats(stats, replay))


def draw_preview(result: dict) -> bool:
    """Show the working frame with detections. Returns False if the user closed it."""
    import cv2

    frame = result["frame"].copy()
    for d in result["detections"]:
        if d.get("x") is None:
            continue
        bgr = (d.get("appearance") or {}).get("dominant_color_bgr") or [255, 255, 255]
        cv2.circle(frame, (d["x"], d["y"]), 18, tuple(int(v) for v in bgr), 2)
        cv2.putText(frame, f"{d['player_id']} {d.get('car') or d.get('skin') or ''}", (d["x"] + 20, d["y"]),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    for i, h in enumerate(result["hud"]):
        cv2.putText(frame, f"{h['zone']}: {h['value']}", (10, 24 + 20 * i),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 255, 200), 1, cv2.LINE_AA)
    cv2.imshow("GameTrainer preview (q to stop)", frame)
    return (cv2.waitKey(1) & 0xFF) != ord("q")


# ------------------------------------------------------------------- parser
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gametrainer",
        description="GameTrainer: track any console game on a CPU-only laptop and replay it from data points.",
    )
    p.add_argument("target", nargs="?",
                   help="Game profile (path, filename, or short name like 'smash') OR a replay.json. Omit to list profiles.")
    p.add_argument("--version", action="version", version=f"GameTrainer {__version__}")

    setup = p.add_argument_group("setup")
    setup.add_argument("--check", action="store_true", help="Check this machine is ready to track")
    setup.add_argument("--wiring", metavar="CONSOLE", help="How to connect a console (switch, ps5, ps4, xbox, ...)")
    setup.add_argument("--list-devices", action="store_true", help="Find the capture card's video index")
    setup.add_argument("--save", action="store_true", help="With --list-devices: save the card's index to ./config/device_config.json")
    setup.add_argument("--calibrate", action="store_true", help="Click players in the live picture to read their colors")
    setup.add_argument("--pick", metavar="X,Y", help="Print the color at X,Y (from --image or the capture device)")
    setup.add_argument("--image", help="Screenshot to use with --pick / --calibrate instead of the capture device")

    track = p.add_argument_group("tracking")
    track.add_argument("--device", default=None, help="Video device index or video file path (overrides device_config.json)")
    track.add_argument("--frames", type=int, default=None, help="Stop after N processed frames")
    track.add_argument("--seconds", type=float, default=None, help="Stop after S seconds")
    track.add_argument("--output", default="./data", help="Output directory for gameplay.db")
    track.add_argument("--preview", action="store_true", help="Show a live window with tracking overlays")
    track.add_argument("--quiet", action="store_true", help="Don't print a line per frame")
    track.add_argument("--synthetic", action="store_true", help="Track a generated test match instead of a capture device")

    rep = p.add_argument_group("replays")
    rep.add_argument("--build-replay", action="store_true", help="Build a data-point replay (after tracking, or from --db)")
    rep.add_argument("--view", action="store_true", help="Open the replay viewer after --build-replay")
    rep.add_argument("--stats", action="store_true", help="Print the per-player scoreboard for a replay")
    rep.add_argument("--replay-output", default="./data/replays/replay.json", help="Path for the built replay JSON")
    rep.add_argument("--db", default=None, help="Database to read (default: <output>/gameplay.db)")
    rep.add_argument("--session", default=None, help="Session id to build a replay from (default: latest)")
    rep.add_argument("--list-sessions", action="store_true", help="List sessions recorded in the database")
    return p


# --------------------------------------------------------------------- main
def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)  # progress lines appear immediately
    except (AttributeError, ValueError):
        pass
    cfg = load_device_config()

    if args.check:
        from middleware.integration.system_check import print_report, run_checks

        print("GameTrainer system check")
        return print_report(run_checks(data_dir=args.output))
    if args.wiring:
        return cmd_wiring(args.wiring)
    if args.list_devices:
        return cmd_list_devices(args.save)
    if args.pick:
        return cmd_pick(args, cfg)
    if args.calibrate:
        if args.target and resolve_profile(args.target) is None:
            print(f"Profile not found: {args.target}")
            return 1
        return cmd_calibrate(args, cfg)

    db_path = Path(args.db) if args.db else Path(args.output) / "gameplay.db"

    # Replay file: scoreboard and/or viewer
    if args.target and is_replay_file(args.target):
        if args.stats:
            print_stats(args.target)
            return 0
        return open_viewer(args.target)

    from middleware.analysis.replay_engine import ReplayEngine

    if args.list_sessions:
        if not db_path.exists():
            print(f"No database at {db_path}")
            return 1
        sessions = ReplayEngine(str(db_path)).load_sessions()
        for s in sessions:
            print(f"  {s['session_id']:32s} {s.get('game') or '-':28s} {s['frame_count']:6d} frames  {s['duration']:8.1f}s")
        if not sessions:
            print("No sessions recorded yet.")
        return 0

    def finish_replay(engine: "ReplayEngine", session_id: str) -> int:
        path = engine.export_replay(engine.build_replay(session_id), args.replay_output)
        print(f"Replay built: {path} (session {session_id})")
        if args.stats:
            print()
            print_stats(path)
        if args.view:
            return open_viewer(path)
        print(f"View it with: gametrainer {path}")
        return 0

    # Build-replay-only mode
    if args.build_replay and not args.target:
        if not db_path.exists():
            print(f"No database at {db_path}. Track a game first.")
            return 1
        engine = ReplayEngine(str(db_path))
        session_id = args.session or engine.latest_session_id()
        if session_id is None:
            print("No sessions found in database.")
            return 1
        return finish_replay(engine, session_id)

    # List profiles
    if args.target is None:
        print(f"GameTrainer {__version__} - CPU-only console game tracker")
        print("Game profiles:")
        for prof in list_profiles():
            try:
                name = json.loads(prof.read_text()).get("name", prof.stem)
            except (OSError, json.JSONDecodeError):
                name = "(invalid JSON)"
            print(f"  {prof.stem:32s} {name}")
        print("\nFirst time? gametrainer --check, then gametrainer --list-devices --save")
        print("Play:       gametrainer <profile> --build-replay --view")
        print("Help:       gametrainer --help")
        return 0

    # Tracking mode
    from middleware.capture.game_tracker import GameTracker

    profile_path = resolve_profile(args.target)
    if profile_path is None:
        print(f"Profile not found: {args.target}")
        print("Available: " + ", ".join(p.stem for p in list_profiles()))
        return 1

    if args.synthetic and args.device is None:
        from middleware.capture.synthetic import make_video

        video = Path(args.output) / "test" / "synthetic_game.mp4"
        if not video.exists():
            make_video(video)
            print(f"Generated synthetic test match: {video}")
        device: Union[int, str] = str(video)
    else:
        device = parse_device(args.device, cfg)
        if isinstance(device, str) and not Path(device).exists():
            print(f"Video file not found: {device}")
            return 1

    try:
        tracker = GameTracker(profile_path, device=device, output_dir=args.output, capture_settings=cfg["capture"])
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Invalid profile {profile_path}: {e}")
        return 1
    for problem in tracker.profile.problems:
        print(f"Profile {problem}")
    for missing in tracker.profile.missing_templates:
        print(f"Warning: template image not found: {missing}")
    try:
        fps, w, h = tracker.start()
    except RuntimeError as e:
        print(f"Capture error: {e}")
        print("Check: console HDMI Out -> capture card HDMI In, card HDMI Out -> TV, card USB -> laptop.")
        print("Find the right index with: gametrainer --list-devices --save   (wiring help: gametrainer --wiring <console>)")
        return 1

    if args.preview and not has_display():
        print("No display found - running without --preview.")
        args.preview = False

    summ = tracker.summary()
    print(f"Tracking '{tracker.profile.name}' ({tracker.profile.console})  session {tracker.session_id}")
    print(f"  device={device}  source {summ['source']} -> working {w}x{h}, every {tracker.profile.process_every_n} "
          f"frame(s), detect at {tracker.profile.detect_scale:g}x, CPU only")
    if tracker.mode_warning:
        print(f"  Warning: {tracker.mode_warning}")
    print(f"  HUD OCR: {'on' if summ['tesseract'] else 'off (install tesseract-ocr + pytesseract to enable)'}")
    print("  Play on the TV as usual. Press Ctrl+C to stop.\n")

    warned_black = False
    try:
        for result in tracker.run(max_frames=args.frames, seconds=args.seconds):
            if tracker.no_signal and not warned_black:
                print("  Warning: the picture has been black for 3 s. PS4/PS5: turn HDCP off. "
                      "Otherwise check the console is on and its HDMI goes into the card's HDMI In.")
                warned_black = True
            if args.preview:
                try:
                    if not draw_preview(result):
                        break
                except Exception as e:  # OpenCV built without GUI support
                    print(f"Preview unavailable ({str(e).splitlines()[0][:80]}); tracking continues without it.")
                    args.preview = False
            if args.quiet:
                continue
            prim = result["primary"]
            where = f"({prim['x']}, {prim['y']})" if prim.get("x") is not None else "not detected"
            players = " ".join(
                f"[{d['player_id']} car={d.get('car')} skin={d.get('skin')}]"
                for d in result["detections"] if d.get("x") is not None
            )
            print(f"  frame {result['frame_number']:5d} | {prim.get('entity', '-'):15s} {where:14s} {players}")
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        tracker.stop()
        if args.preview:
            import cv2

            try:
                cv2.destroyAllWindows()
            except Exception:
                pass

    summ = tracker.summary()
    print(f"\nSession {tracker.session_id}: processed {summ['frames_processed']} of {summ['frames_read']} frames -> {tracker.db_path}")

    if args.build_replay:
        if summ["frames_processed"] == 0:
            print("No frames processed - nothing to replay.")
            return 1
        return finish_replay(ReplayEngine(str(tracker.db_path)), tracker.session_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
