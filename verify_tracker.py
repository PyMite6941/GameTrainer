#!/usr/bin/env python3
"""End-to-end verification of GameTrainer without a capture card.

Generates a synthetic match (green player, red opponent, orange sprite), then checks:

  1. tracking accuracy against the known ground-truth positions
  2. players are not confused with each other (hue tolerance)
  3. appearance: measured skin/car colors are right
  4. two runs are stored as two separate sessions
  5. the replay engine rebuilds each session from data points
  6. older databases (no session ids) still build replays
  7. the replay viewer renders headlessly
  8. the command-line entry point (list, track by short name, build, sessions)
  9. the middleware modules: stats, simulator, color picker, frame processor,
     black-picture detection, profile validation, capture, run_session pipeline,
     capture-mode parsing, wiring notes, system check
 10. the existing analyzer and player profiler still read the database

Run:  python verify_tracker.py         (exit code 0 = all checks passed)
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import sys
import tempfile
import time
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from middleware.analysis.replay_engine import ReplayEngine  # noqa: E402
from middleware.capture import synthetic  # noqa: E402
from middleware.capture.game_tracker import GameTracker  # noqa: E402

FRAMES = 120
PROFILE = REPO / "config" / "games" / "switch_smash_bros_ultimate.json"
results = []


def check(name: str, cond: bool, detail: str = "") -> None:
    results.append((name, cond))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}{(' - ' + detail) if detail else ''}")


def track(video: Path, out: Path, every_n: int = 1) -> GameTracker:
    tracker = GameTracker(PROFILE, device=str(video), output_dir=str(out))
    tracker.profile.process_every_n = every_n
    tracker.profile.roi = None
    tracker.start()
    errs = {"p1": [], "p2": []}
    swapped = 0
    for res in tracker.run():
        i = tracker.frame_count - 1
        truth = {"p1": synthetic.player_pos(i, FRAMES), "p2": synthetic.opponent_pos(i, FRAMES)}
        for d in res["detections"]:
            if d.get("x") is None:
                continue
            tx, ty = truth[d["player_id"]]
            errs[d["player_id"]].append(math.hypot(d["x"] - tx, d["y"] - ty))
            other = truth["p2" if d["player_id"] == "p1" else "p1"]
            if math.hypot(d["x"] - other[0], d["y"] - other[1]) < 10 and math.hypot(d["x"] - tx, d["y"] - ty) > 10:
                swapped += 1
    tracker.errs, tracker.swapped = errs, swapped
    return tracker


def main() -> int:
    t_start = time.time()
    tmp = Path(tempfile.mkdtemp(prefix="gametrainer-verify-"))
    video = synthetic.make_video(tmp / "synthetic_game.mp4", frames=FRAMES)
    out = tmp / "data"
    db = out / "gameplay.db"
    print(f"Working in {tmp}\n")

    print("Tracking")
    t0 = time.time()
    tr1 = track(video, out)
    fps = tr1.processed_count / max(1e-6, time.time() - t0)
    for pid in ("p1", "p2"):
        e = tr1.errs[pid]
        mean = sum(e) / len(e) if e else float("inf")
        check(f"{pid} detected in every frame", len(e) == FRAMES, f"{len(e)}/{FRAMES}")
        check(f"{pid} position error < 3px", mean < 3, f"mean {mean:.2f}px")
    check("players never swapped", tr1.swapped == 0, f"{tr1.swapped} swaps")
    import cv2

    cap = cv2.VideoCapture(str(video))
    frames = []
    while len(frames) < 60:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    cap.release()
    bench = GameTracker(PROFILE, device=str(video), output_dir=str(tmp / "bench"))
    t0 = time.time()
    for i, f in enumerate(frames):
        bench.process_frame(f, i)
    proc_fps = len(frames) / max(1e-6, time.time() - t0)
    bench.stop()
    load = os.getloadavg()[0] / (os.cpu_count() or 1) if hasattr(os, "getloadavg") else 0.0
    detail = f"{proc_fps:.0f} fps tracking, {fps:.0f} fps incl. MP4 decode, 1280x720, 2 players"
    if load > 1.0:
        # Other programs are saturating the CPU; only catch real regressions.
        check("tracking >= 10 fps (machine busy, 30 fps target not enforced)", proc_fps >= 10,
              f"{detail}; load {load:.1f} per core")
    else:
        check("tracking >= 30 fps on this CPU", proc_fps >= 30, detail)

    print("\nAppearance")
    conn = sqlite3.connect(db)
    skins = dict(conn.execute("SELECT player_id, skin FROM tracked_entities GROUP BY player_id"))
    check("p1 skin measured as green", skins.get("p1") == "green", str(skins.get("p1")))
    check("p2 skin measured as red", skins.get("p2") == "red", str(skins.get("p2")))

    print("\nSessions")
    tr2 = track(video, out, every_n=2)
    sessions = ReplayEngine(str(db)).load_sessions()
    ids = [s["session_id"] for s in sessions]
    check("two runs -> two sessions", ids == [tr1.session_id, tr2.session_id], str(ids))
    counts = {s["session_id"]: s["frame_count"] for s in sessions}
    check("session frame counts kept apart", counts.get(tr1.session_id) == FRAMES and counts.get(tr2.session_id) == FRAMES // 2, str(counts))

    print("\nReplay")
    engine = ReplayEngine(str(db))
    rep = engine.build_replay(tr1.session_id)
    path = engine.export_replay(rep, str(out / "replays" / "replay.json"))
    check("replay has every frame", len(rep["timeline"]) == FRAMES, str(len(rep["timeline"])))
    check("replay players are p1 and p2", sorted(rep["players"]) == ["p1", "p2"], str(sorted(rep["players"])))
    check("replay knows the game and frame size", rep["game"] == "Super Smash Bros. Ultimate" and rep["frame_size"] == [1280, 720])
    p1 = rep["players"]["p1"]
    pts = [synthetic.player_pos(i, FRAMES) for i in range(FRAMES)]
    true_len = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
    err = abs(p1["distance_traveled_px"] - true_len) / true_len
    check("p1 distance matches true path within 5%", err < 0.05, f"{p1['distance_traveled_px']:.0f}px vs {true_len:.0f}px")
    check("p1 color is green", p1["color_bgr"] and p1["color_bgr"][1] > 150 and p1["color_bgr"][2] < 60, str(p1["color_bgr"]))
    latest = engine.build_replay()
    check("default replay = latest session", latest["session_id"] == tr2.session_id)
    size_kb = Path(path).stat().st_size / 1024
    video_kb = video.stat().st_size / 1024
    check("replay.json smaller than the video", size_kb < video_kb, f"{size_kb:.0f} KB vs {video_kb:.0f} KB video")

    print("\nLegacy database")
    legacy = tmp / "legacy.db"
    lc = sqlite3.connect(legacy)
    lc.execute("CREATE TABLE frames (id INTEGER PRIMARY KEY, timestamp REAL, frame_number INTEGER, roi_x INTEGER, roi_y INTEGER, roi_width INTEGER, roi_height INTEGER, opponent_x INTEGER, opponent_y INTEGER, opponent_state TEXT, frame_data BLOB)")
    lc.execute("CREATE TABLE tracked_entities (id INTEGER PRIMARY KEY, timestamp REAL, frame_number INTEGER, entity_name TEXT, x INTEGER, y INTEGER, confidence REAL, value TEXT, method TEXT)")
    base = 1_700_000_000.0
    for i in range(10):
        lc.execute("INSERT INTO frames (timestamp, frame_number, opponent_x, opponent_y) VALUES (?, ?, ?, ?)", (base + i, i, i * 10, 5))
        lc.execute("INSERT INTO tracked_entities (timestamp, frame_number, entity_name, x, y, method) VALUES (?, ?, 'opponent', ?, 5, 'color')", (base + i, i, i * 10))
    lc.commit()
    lc.close()
    leg = ReplayEngine(str(legacy))
    lrep = leg.build_replay()
    check("old database builds a replay", len(lrep["timeline"]) == 10 and "opponent" in lrep["players"], lrep["session_id"])

    print("\nViewer (headless)")
    try:
        from middleware.simulation.replay_viewer import ReplayViewer

        v = ReplayViewer(path)
        v.init_display()
        v.seek(rep["duration_seconds"] / 2)
        v.update(0.1)
        snap = v.save_snapshot(str(tmp / "viewer.png"))
        v.run(max_seconds=0.3, autoplay=True)
        check("viewer renders and plays", Path(snap).stat().st_size > 1000 and v.playhead > 0, snap)
    except Exception as e:  # pragma: no cover - reported as a failure
        check("viewer renders and plays", False, repr(e))

    print("\nCommand line")
    import track_game

    def cli(*argv):
        buf = StringIO()
        with redirect_stdout(buf):
            code = track_game.main(list(argv))
        return code, buf.getvalue()

    code, text = cli()
    check("lists profiles", code == 0 and "switch_smash_bros_ultimate" in text)
    check("profile JSON isn't mistaken for a replay", not track_game.is_replay_file(str(REPO / "config/games/console_generic.json")))
    check("replay JSON is recognised", track_game.is_replay_file(path))
    check("short profile names resolve", track_game.resolve_profile("smash") == PROFILE.resolve() or track_game.resolve_profile("smash").name == PROFILE.name)
    cli_out = tmp / "cli"
    code, text = cli("smash", "--device", str(video), "--output", str(cli_out), "--frames", "20", "--quiet",
                     "--build-replay", "--replay-output", str(cli_out / "r.json"))
    check("track + build replay via CLI", code == 0 and (cli_out / "r.json").exists(), text.strip().splitlines()[-1] if text else "")
    code, text = cli("--list-sessions", "--output", str(cli_out))
    check("list sessions via CLI", code == 0 and "Super Smash" in text)
    code, text = cli("--build-replay", "--output", str(cli_out), "--replay-output", str(cli_out / "r2.json"))
    check("build replay later via CLI", code == 0 and (cli_out / "r2.json").exists())
    code, text = cli("not_a_game")
    check("unknown profile fails cleanly", code == 1 and "Profile not found" in text)

    print("\nMiddleware")
    import numpy as np

    from middleware.analysis.feature_extractor import extract_features
    from middleware.analysis.frame_processor import FrameProcessor, GameProfile, sample_color
    from middleware.capture.hdmi_capture import HdmiCapture
    from middleware.capture.usb_capture import list_devices
    from middleware.integration.system_check import run_checks
    from middleware.integration.system_integration import run_session
    from middleware.simulation.game_simulator import GameSimulator
    from hardware_tools.adapters.hdmi_adapter import console_setup
    from hardware_tools.drivers.capture_card_driver import best_mode, parse_v4l2_formats

    stats = rep.get("stats", {}).get("players", {})
    check("replay carries per-player stats", set(stats) == {"p1", "p2"} and stats["p1"]["on_screen_pct"] == 100.0,
          str({k: v["avg_speed_px_s"] for k, v in stats.items()}))
    true_speed = true_len / rep["duration_seconds"] if rep["duration_seconds"] else 0
    check("stats speed matches the data", abs(extract_features(rep)["players"]["p1"]["avg_speed_px_s"] - true_speed) / max(1, true_speed) < 0.1,
          f"{stats['p1']['avg_speed_px_s']} px/s vs {true_speed:.0f} px/s")

    sim = GameSimulator(rep)
    a_, b_ = rep["timeline"][10], rep["timeline"][11]
    mid = (a_["t"] + b_["t"]) / 2
    pa = next(e for e in a_["entities"] if e["player_id"] == "p1")
    pb = next(e for e in b_["entities"] if e["player_id"] == "p1")
    st = sim.state_at(mid)["players"]["p1"]
    check("simulator interpolates between samples", abs(st["x"] - (pa["x"] + pb["x"]) / 2) < 1.0, f"x={st['x']:.1f}")
    states = list(sim.play(fps=60))
    check("simulator streams at a fixed rate", abs(len(states) - rep["duration_seconds"] * 60) <= 2, f"{len(states)} states")

    cap0 = cv2.VideoCapture(str(video))
    _, first = cap0.read()
    cap0.release()
    picked = sample_color(first, *synthetic.player_pos(0, FRAMES))
    check("color picker reads the player's color", picked["color_name"] == "green" and picked["color_bgr"][1] > 150, str(picked["color_bgr"]))
    proc = FrameProcessor(GameProfile(PROFILE))
    proc.profile.roi = None
    res = proc.process(first)
    check("frame processor works standalone", {d["player_id"] for d in res["detections"]} == {"p1", "p2"} and not res["black"])
    check("black picture is flagged", proc.process(np.zeros_like(first))["black"])

    bad = tmp / "bad_profile.json"
    bad.write_text(json.dumps({"name": "bad", "entities": [{"name": "a", "method": "color", "color_bgr": [0, 0]}]}))
    try:
        GameProfile(bad)
        check("invalid profiles are rejected", False)
    except ValueError as e:
        check("invalid profiles are rejected", "color_bgr" in str(e), str(e)[:60])

    with HdmiCapture(str(video), downscale_width=640) as cap:
        f = cap.read()
        check("HDMI capture downscales to working size", f is not None and f.shape[1] == 640 and cap.info()["source"] == "1280x720")
    check("device discovery runs", isinstance(list_devices(3), list))

    sess = run_session(PROFILE, device=str(video), output=tmp / "pipeline", frames=30)
    check("run_session pipeline: track -> replay -> stats", sess.frames_processed == 30 and sess.replay_path.exists()
          and set(sess.stats["players"]) == {"p1", "p2"}, str(sess.replay_path.name))

    modes = parse_v4l2_formats("[0]: 'MJPG' (Motion-JPEG)\n\tSize: Discrete 1920x1080\n\t\tInterval: Discrete 0.017s (60.000 fps)\n"
                               "[1]: 'YUYV' (YUYV 4:2:2)\n\tSize: Discrete 1920x1080\n\t\tInterval: Discrete 0.200s (5.000 fps)\n")
    check("capture mode parser picks MJPG 1080p60", str(best_mode(modes)) == "MJPG 1920x1080 @ 60 fps", str(best_mode(modes)))
    check("console wiring notes exist", "HDCP" in console_setup("ps5")["hdcp"])
    checks_ = run_checks(probe_devices=False, data_dir=str(tmp / "check"))
    check("system check passes on this machine", not any(c.status == "FAIL" for c in checks_),
          "; ".join(f"{c.name}: {c.detail}" for c in checks_ if c.status == "FAIL"))

    print("\nAnalyzer / profiler")
    try:
        cwd = os.getcwd()
        os.chdir(tmp)
        from analyzer import OpponentAnalyzer
        from player_profiler import create_player_profile

        with redirect_stdout(StringIO()):
            OpponentAnalyzer(str(db)).save_profile()
            pp = create_player_profile("verify_player", str(db))
        check("analyzer + profiler read the DB", pp.profile_id == "verify_player")
    except Exception as e:
        check("analyzer + profiler read the DB", False, repr(e))
    finally:
        os.chdir(cwd)

    passed = sum(1 for _, ok in results if ok)
    print(f"\n{passed}/{len(results)} checks passed in {time.time() - t_start:.1f}s")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
