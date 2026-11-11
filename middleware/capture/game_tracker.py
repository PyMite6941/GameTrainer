"""
GameTracker - game-agnostic, CPU-only gameplay tracking for console capture feeds.

Ties the middleware together for one tracking run (a *session*):

    HdmiCapture (capture card or video file)
        -> FrameProcessor (color / template / motion detection, appearance, HUD OCR)
        -> gameplay.db (sessions, frames, tracked_entities, hud_readings, game_states)

The ReplayEngine later rebuilds the match from those data points - no video is
stored. Per-game behavior lives entirely in a JSON game profile in
config/games/, so adding a game needs no code changes.

Leetify for CS2 reads demo logs; consoles expose no logs, so the console
equivalent is screen-capture computer vision - the same information a human
player sees on screen.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union

import numpy as np

from middleware.analysis.frame_processor import (  # noqa: F401  (re-exported)
    DEFAULT_HUE_TOLERANCE,
    MAX_HUE_TOLERANCE,
    TESSERACT_AVAILABLE,
    FrameProcessor,
    GameProfile,
    color_name,
)
from middleware.capture.hdmi_capture import HdmiCapture, open_capture  # noqa: F401

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        game TEXT, console TEXT, profile TEXT, device TEXT,
        started_at REAL, ended_at REAL,
        work_width INTEGER, work_height INTEGER, fps INTEGER,
        frames_processed INTEGER)""",
    """CREATE TABLE IF NOT EXISTS frames (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp REAL NOT NULL,
        frame_number INTEGER NOT NULL,
        roi_x INTEGER, roi_y INTEGER, roi_width INTEGER, roi_height INTEGER,
        opponent_x INTEGER, opponent_y INTEGER, opponent_state TEXT,
        frame_data BLOB)""",
    """CREATE TABLE IF NOT EXISTS game_states (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp REAL NOT NULL,
        player_health INTEGER, current_animation TEXT,
        action_state TEXT, level TEXT, game_mode TEXT)""",
    """CREATE TABLE IF NOT EXISTS tracked_entities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp REAL NOT NULL,
        frame_number INTEGER NOT NULL,
        entity_name TEXT NOT NULL,
        x INTEGER, y INTEGER,
        confidence REAL,
        value TEXT,
        method TEXT)""",
    """CREATE TABLE IF NOT EXISTS hud_readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp REAL NOT NULL,
        frame_number INTEGER NOT NULL,
        zone_name TEXT NOT NULL,
        value TEXT,
        raw_text TEXT)""",
]

# Columns added since the first schema; backfilled on older databases.
ADDED_COLUMNS = {
    "frames": ["session_id TEXT"],
    "game_states": ["session_id TEXT", "frame_number INTEGER"],
    "tracked_entities": ["session_id TEXT", "player_id TEXT", "appearance_signature TEXT", "car TEXT", "skin TEXT"],
    "hud_readings": ["session_id TEXT"],
}


def init_database(db_path: Union[str, Path]) -> None:
    """Create or upgrade a gameplay database in place (never drops data)."""
    conn = sqlite3.connect(db_path)
    try:
        c = conn.cursor()
        for stmt in SCHEMA:
            c.execute(stmt)
        for table, cols in ADDED_COLUMNS.items():
            existing = {row[1] for row in c.execute(f"PRAGMA table_info({table})")}
            for col in cols:
                if col.split()[0] not in existing:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {col}")
        for table in ADDED_COLUMNS:
            c.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_session ON {table}(session_id)")
        conn.commit()
    finally:
        conn.close()


class GameTracker:
    def __init__(
        self,
        game_profile: Union[str, Path, GameProfile],
        device: Union[int, str] = 0,
        output_dir: str = "./data",
        capture_settings: Optional[Dict[str, Any]] = None,
    ):
        self.profile = game_profile if isinstance(game_profile, GameProfile) else GameProfile(game_profile)
        self.device = device
        self.capture_settings = dict(capture_settings or {})
        self.profile.apply_machine_limits(self.capture_settings)
        self.processor = FrameProcessor(self.profile)
        self.capture: Optional[HdmiCapture] = None

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.output_dir / "gameplay.db"
        self.session_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

        self.fps = 30
        self.source_width = 0
        self.source_height = 0
        self.work_w = 0
        self.work_h = 0
        self.processed_count = 0
        self.no_signal = False
        self._conn: Optional[sqlite3.Connection] = None
        self._pending = 0
        self.commit_every = 30

        init_database(self.db_path)

    # --------------------------------------------------------------- properties
    @property
    def frame_count(self) -> int:
        return self.capture.frames_read if self.capture else 0

    @property
    def mode_warning(self) -> Optional[str]:
        return self.capture.mode_mismatch() if self.capture else None

    # ---------------------------------------------------------------------- db
    def _db(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
        return self._conn

    def _flush(self) -> None:
        if self._conn is not None:
            self._conn.commit()
        self._pending = 0

    # ----------------------------------------------------------------- capture
    def start(self) -> tuple:
        """Open the capture device and register the session. Returns (fps, work_w, work_h)."""
        self.capture = HdmiCapture.from_config(self.device, self.capture_settings, self.profile.downscale_width)
        self.fps, self.work_w, self.work_h = self.capture.open()
        self.source_width, self.source_height = self.capture.source_width, self.capture.source_height
        conn = self._db()
        conn.execute(
            """INSERT OR REPLACE INTO sessions
               (session_id, game, console, profile, device, started_at,
                work_width, work_height, fps, frames_processed)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (self.session_id, self.profile.name, self.profile.console, str(self.profile.path),
             str(self.device), time.time(), self.work_w, self.work_h, self.fps),
        )
        conn.commit()
        return self.fps, self.work_w, self.work_h

    def read(self) -> Optional[np.ndarray]:
        return self.capture.read() if self.capture else None

    def stop(self) -> None:
        if self.capture is not None:
            self.capture.close()
        if self._conn is not None:
            self._conn.execute(
                "UPDATE sessions SET ended_at = ?, frames_processed = ? WHERE session_id = ?",
                (time.time(), self.processed_count, self.session_id),
            )
            self._flush()
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------- frame
    def process_frame(
        self,
        frame: np.ndarray,
        frame_number: int,
        game_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Detect everything in one working frame and store it in the session."""
        timestamp = self.capture.last_timestamp if self.capture is not None and self.capture.last_timestamp else time.time()
        result = self.processor.process(frame, frame_number)
        if self.capture is not None:
            self.capture.note_brightness(result["black"])
            self.no_signal = self.capture.no_signal
        detections, primary, hud = result["detections"], result["primary"], result["hud"]
        x1, y1, x2, y2 = result["roi"]

        c = self._db()
        c.execute(
            """INSERT INTO frames
               (session_id, timestamp, frame_number, roi_x, roi_y, roi_width, roi_height,
                opponent_x, opponent_y, opponent_state, frame_data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (self.session_id, timestamp, frame_number, x1, y1, x2 - x1, y2 - y1,
             primary["x"], primary["y"], primary.get("method") or "none", None),
        )
        if game_data:
            c.execute(
                """INSERT INTO game_states
                   (session_id, frame_number, timestamp, player_health, current_animation,
                    action_state, level, game_mode)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (self.session_id, frame_number, timestamp, game_data.get("player_health"),
                 game_data.get("current_animation"), game_data.get("action_state"),
                 game_data.get("level"), game_data.get("game_mode")),
            )
        c.executemany(
            """INSERT INTO tracked_entities
               (session_id, timestamp, frame_number, entity_name, player_id, x, y, confidence,
                value, method, appearance_signature, car, skin)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (self.session_id, timestamp, frame_number, d["entity"], d.get("player_id"),
                 d.get("x"), d.get("y"), d.get("confidence"), d.get("value"), d.get("method"),
                 json.dumps(d["appearance"]) if d.get("appearance") else None, d.get("car"), d.get("skin"))
                for d in detections
            ],
        )
        # Only store HUD values when freshly read, to keep the database small.
        c.executemany(
            """INSERT INTO hud_readings
               (session_id, timestamp, frame_number, zone_name, value, raw_text)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [(self.session_id, timestamp, frame_number, h["zone"], h["value"], h["value"]) for h in hud if h["fresh"]],
        )
        self._pending += 1
        if self._pending >= self.commit_every:
            self._flush()

        self.processed_count += 1
        return {
            "frame_number": frame_number,
            "timestamp": timestamp,
            "primary": primary,
            "detections": detections,
            "hud": hud,
            "black": result["black"],
            "frame": frame,
        }

    def run(
        self,
        max_frames: Optional[int] = None,
        seconds: Optional[float] = None,
        game_data_fn=None,
    ) -> Iterator[Dict[str, Any]]:
        """Capture loop. Yields per-frame detection results.

        game_data_fn(frame_number) -> dict, logged into game_states (health, level, ...).
        """
        if self.capture is None or self.capture.cap is None:
            self.start()
        start = time.time()
        frame_number = 0
        try:
            while True:
                if max_frames is not None and frame_number >= max_frames:
                    break
                if seconds is not None and (time.time() - start) >= seconds:
                    break
                frame = self.read()
                if frame is None:
                    break
                if self.frame_count % self.profile.process_every_n != 0:
                    continue
                game_data = game_data_fn(frame_number) if game_data_fn else None
                yield self.process_frame(frame, frame_number, game_data)
                frame_number += 1
        finally:
            self.stop()

    # ------------------------------------------------------------------- stats
    def summary(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "game": self.profile.name,
            "console": self.profile.console,
            "source": f"{self.source_width}x{self.source_height}",
            "working": f"{self.work_w}x{self.work_h}",
            "fps": self.fps,
            "frames_read": self.frame_count,
            "frames_processed": self.processed_count,
            "process_every_n": self.profile.process_every_n,
            "detect_scale": self.profile.detect_scale,
            "tesseract": TESSERACT_AVAILABLE,
        }


def list_profiles(profiles_dir: Union[str, Path, None] = None) -> List[Path]:
    if profiles_dir is None:
        profiles_dir = Path(__file__).resolve().parents[2] / "config" / "games"
    return sorted(Path(profiles_dir).glob("*.json"))
