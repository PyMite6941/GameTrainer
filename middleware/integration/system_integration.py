"""
System integration: config discovery and the one-call tracking pipeline.

Config lookup (same for source checkouts, pip installs and the one-file binary):
  1. ./config/ in the folder you run from  (your edits win)
  2. the bundled config/ next to the code  (defaults)

Pipeline:
    from middleware.integration.system_integration import run_session
    result = run_session("smash", device=0, seconds=300)
    print(result.replay_path, result.stats["players"]["p1"]["avg_speed_px_s"])

run_session = open capture -> track -> store session -> build replay ->
compute stats, returning paths and numbers. track_game.py is the CLI around it.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

# Bundled files: the PyInstaller unpack dir when frozen, else the source tree.
APP_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))

DEFAULT_DEVICE_CONFIG: Dict[str, Any] = {
    "device": {"index": 0},
    "capture": {
        "width": 1920,
        "height": 1080,
        "fps": 60,
        "fourcc": "MJPG",
        "downscale_width": 1280,
        "process_every_n_frames": 2,
        "detect_scale": 0.5,
    },
}


def user_dir() -> Path:
    """Where user-editable config and data live: the current directory."""
    return Path.cwd()


def config_dirs() -> List[Path]:
    """Config search order: ./config (user overrides) then the bundled config."""
    out: List[Path] = []
    for d in (user_dir() / "config", APP_DIR / "config"):
        if d.is_dir() and d.resolve() not in [o.resolve() for o in out]:
            out.append(d)
    return out


def list_profiles() -> List[Path]:
    """All game profiles; a user copy overrides a bundled one with the same filename."""
    seen: Dict[str, Path] = {}
    for d in config_dirs():
        for p in sorted((d / "games").glob("*.json")):
            seen.setdefault(p.name, p)
    return [seen[k] for k in sorted(seen)]


def resolve_profile(target: str) -> Optional[Path]:
    """Accept a path, a profile filename, or a short name like 'smash'."""
    p = Path(target)
    if p.is_file():
        return p
    profiles = list_profiles()
    for prof in profiles:
        if prof.name == p.name or prof.stem == target:
            return prof
    matches = [prof for prof in profiles if target.lower() in prof.stem.lower()]
    return matches[0] if len(matches) == 1 else None


def device_config_path() -> Optional[Path]:
    for d in config_dirs():
        path = d / "device_config.json"
        if path.is_file():
            return path
    return None


def load_device_config(warn: Callable[[str], None] = print) -> Dict[str, Any]:
    """device_config.json merged over the defaults (missing keys fall back)."""
    cfg = json.loads(json.dumps(DEFAULT_DEVICE_CONFIG))
    path = device_config_path()
    if path is None:
        return cfg
    try:
        with open(path) as f:
            user = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        warn(f"Warning: ignoring invalid {path}: {e}")
        return cfg
    for section in ("device", "capture"):
        if isinstance(user.get(section), dict):
            cfg[section].update({k: v for k, v in user[section].items() if k != "note"})
    return cfg


def save_device_index(index: int, path: Optional[Path] = None) -> Path:
    """Set device.index in the user's ./config/device_config.json, keeping other keys."""
    path = path or (user_dir() / "config" / "device_config.json")
    data: Dict[str, Any] = {}
    if path.is_file():
        with open(path) as f:
            data = json.load(f)
    else:
        bundled = APP_DIR / "config" / "device_config.json"
        if bundled.is_file():
            with open(bundled) as f:
                data = json.load(f)
    data.setdefault("device", {})["index"] = int(index)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")
    return path


@dataclass
class SessionResult:
    session_id: str
    db_path: Path
    frames_processed: int
    replay_path: Optional[Path] = None
    stats: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


def run_session(
    profile: Union[str, Path],
    device: Union[int, str, None] = None,
    output: Union[str, Path] = "./data",
    seconds: Optional[float] = None,
    frames: Optional[int] = None,
    replay_output: Union[str, Path, None] = None,
    capture_settings: Optional[Dict[str, Any]] = None,
    on_frame: Optional[Callable[[Dict[str, Any]], Optional[bool]]] = None,
) -> SessionResult:
    """Track one session end to end and build its replay and stats.

    on_frame(result) is called for every processed frame; return False to stop.
    """
    from middleware.analysis.feature_extractor import extract_features
    from middleware.analysis.replay_engine import ReplayEngine
    from middleware.capture.game_tracker import GameTracker

    profile_path = resolve_profile(str(profile))
    if profile_path is None:
        raise FileNotFoundError(f"Profile not found: {profile}")
    cfg = load_device_config()
    if device is None:
        device = int(cfg["device"].get("index", 0))
    tracker = GameTracker(profile_path, device=device, output_dir=str(output),
                          capture_settings=capture_settings or cfg["capture"])
    tracker.start()
    warnings = [f"template image not found: {m}" for m in tracker.profile.missing_templates]
    if tracker.mode_warning:
        warnings.append(tracker.mode_warning)
    try:
        for res in tracker.run(max_frames=frames, seconds=seconds):
            if on_frame is not None and on_frame(res) is False:
                break
    finally:
        tracker.stop()
    if tracker.no_signal:
        warnings.append("picture was black - check HDCP (PS4/PS5) and the console's HDMI output")

    result = SessionResult(tracker.session_id, tracker.db_path, tracker.processed_count, warnings=warnings)
    if tracker.processed_count:
        engine = ReplayEngine(str(tracker.db_path))
        replay = engine.build_replay(tracker.session_id)
        out = replay_output or Path(output) / "replays" / f"{tracker.session_id}.json"
        result.replay_path = Path(engine.export_replay(replay, str(out)))
        result.stats = replay.get("stats") or extract_features(replay)
    return result


System_Integration = run_session
