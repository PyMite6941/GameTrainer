"""
Replay Engine — Leetify-style analysis from gameplay data points (no video).

Reads gameplay.db (frames, tracked_entities, hud_readings, game_states) and
reconstructs a match entirely from data points:

  * timeline          — per-frame position of every tracked player/entity
  * events            — kills, objectives, zone entries/exits, HUD changes
  * stats             — distance traveled, time in zones, damage, lap/position
  * appearance        — car/skin/body color per player across the session
  * replay.json       — portable, video-free replay you can scrub through

The replay viewer (replay_viewer.py) renders this JSON in Pygame: entities as
colored sprites with their captured car/skin appearance, no source video needed.

Usage:
    from middleware.analysis.replay_engine import ReplayEngine
    engine = ReplayEngine("./data/gameplay.db")
    replay = engine.build_replay()          # latest session; or pass a session_id
    engine.export_replay(replay, "./data/replays/replay.json")
"""

from __future__ import annotations

import bisect
import json
import math
import sqlite3
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ReplayEngine:
    def __init__(self, db_path: str = "./data/gameplay.db"):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

    # ------------------------------------------------------------------ load
    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _columns(self, conn: sqlite3.Connection, table: str) -> set:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}

    def _has_table(self, conn: sqlite3.Connection, table: str) -> bool:
        return (
            conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            is not None
        )

    def load_sessions(self) -> List[Dict[str, Any]]:
        """List capture sessions, oldest first.

        Runs recorded by the current tracker carry a session_id. Frames from older
        databases (no session_id) are grouped into 5-minute buckets and given
        ids of the form legacy_<n>_<start-timestamp>.
        """
        conn = self._connect()
        sessions: List[Dict[str, Any]] = []
        has_sid = "session_id" in self._columns(conn, "frames")
        if has_sid and self._has_table(conn, "sessions"):
            for sid, game, console, w, h, fps, t0, t1, n in conn.execute(
                """SELECT s.session_id, s.game, s.console, s.work_width, s.work_height, s.fps,
                          MIN(f.timestamp), MAX(f.timestamp), COUNT(f.id)
                   FROM sessions s JOIN frames f ON f.session_id = s.session_id
                   GROUP BY s.session_id ORDER BY MIN(f.timestamp)"""
            ):
                sessions.append(
                    {
                        "session_id": sid,
                        "game": game,
                        "console": console,
                        "work_width": w,
                        "work_height": h,
                        "fps": fps,
                        "start": t0,
                        "end": t1,
                        "frame_count": n,
                        "duration": round(t1 - t0, 2),
                    }
                )
        legacy_where = "WHERE session_id IS NULL" if has_sid else ""
        rows = conn.execute(
            f"""SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM frames {legacy_where}
                GROUP BY CAST(timestamp AS INTEGER) / 300 ORDER BY MIN(timestamp)"""
        ).fetchall()
        conn.close()
        for i, (t0, t1, n) in enumerate(rows):
            sessions.append(
                {
                    "session_id": f"legacy_{i}_{int(t0)}",
                    "game": None,
                    "console": None,
                    "work_width": None,
                    "work_height": None,
                    "fps": None,
                    "start": t0,
                    "end": t1,
                    "frame_count": n,
                    "duration": round(t1 - t0, 2),
                }
            )
        sessions.sort(key=lambda s: s["start"])
        return sessions

    def latest_session_id(self) -> Optional[str]:
        sessions = self.load_sessions()
        return sessions[-1]["session_id"] if sessions else None

    def _session_filter(
        self, conn: sqlite3.Connection, table: str, session_id: Optional[str]
    ) -> Tuple[str, List[Any]]:
        """WHERE clause selecting one session's rows from a table."""
        if not session_id:
            return "", []
        if "session_id" in self._columns(conn, table) and not session_id.startswith(
            ("legacy_", "session_")
        ):
            return " WHERE session_id = ?", [session_id]
        # Legacy bucket: legacy_<n>_<t0> (or the old session_<n>_<t0> spelling)
        try:
            t0 = float(session_id.split("_")[-1])
        except ValueError:
            return " WHERE 1 = 0", []
        bucket = int(t0) // 300
        clause = " WHERE CAST(timestamp AS INTEGER) / 300 = ?"
        if "session_id" in self._columns(conn, table):
            clause += " AND session_id IS NULL"
        return clause, [bucket]

    def _load(
        self, table: str, columns: List[str], session_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        conn = self._connect()
        if not self._has_table(conn, table):
            conn.close()
            return []
        available = self._columns(conn, table)
        select = ", ".join(c if c in available else f"NULL AS {c}" for c in columns)
        where, params = self._session_filter(conn, table, session_id)
        cur = conn.execute(f"SELECT {select} FROM {table}{where} ORDER BY timestamp, id", params)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        conn.close()
        return rows

    def load_frames(
        self, session_id: Optional[str] = None, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        rows = self._load(
            "frames",
            ["id", "timestamp", "frame_number", "roi_x", "roi_y", "roi_width", "roi_height",
             "opponent_x", "opponent_y", "opponent_state"],
            session_id,
        )
        return rows[:limit] if limit else rows

    def load_entities(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        rows = self._load(
            "tracked_entities",
            ["id", "timestamp", "frame_number", "entity_name", "player_id", "x", "y",
             "confidence", "value", "method", "appearance_signature", "car", "skin"],
            session_id,
        )
        for row in rows:
            if row.get("appearance_signature"):
                try:
                    row["appearance_signature"] = json.loads(row["appearance_signature"])
                except (json.JSONDecodeError, TypeError):
                    row["appearance_signature"] = {}
        return rows

    def load_hud(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self._load(
            "hud_readings", ["id", "timestamp", "frame_number", "zone_name", "value"], session_id
        )

    def load_game_states(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self._load(
            "game_states",
            ["id", "timestamp", "frame_number", "player_health", "current_animation",
             "action_state", "level", "game_mode"],
            session_id,
        )

    def _session_info(self, session_id: Optional[str]) -> Dict[str, Any]:
        for s in self.load_sessions():
            if s["session_id"] == session_id:
                return s
        return {}

    # ------------------------------------------------------------------ build
    def build_replay(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Reconstruct a full match from data points. Returns a replay dict.

        With no session_id the most recent session is used.
        """
        if session_id is None:
            session_id = self.latest_session_id()
        info = self._session_info(session_id) if session_id else {}
        frames = self.load_frames(session_id)
        entities = self.load_entities(session_id)
        hud = self.load_hud(session_id)
        states = self.load_game_states(session_id)

        replay: Dict[str, Any] = {
            "format_version": 2,
            "session_id": session_id or "unknown",
            "game": info.get("game"),
            "console": info.get("console"),
            "frame_size": [info.get("work_width"), info.get("work_height")],
            "start_timestamp": None,
            "duration_seconds": 0.0,
            "total_frames": len(frames),
            "players": {},
            "events": [],
            "damage_events": [],
            "timeline": [],
            "metadata": {
                "generated_at": time.time(),
                "source_db": str(self.db_path),
                "note": "Reconstructed from data points - no source video required.",
            },
        }
        if not frames:
            return replay

        start_ts = frames[0]["timestamp"]
        replay["start_timestamp"] = start_ts
        replay["duration_seconds"] = round(frames[-1]["timestamp"] - start_ts, 2)

        by_frame: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for e in entities:
            by_frame[e["frame_number"]].append(e)
        hud_by_frame: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for h in hud:
            hud_by_frame[h["frame_number"]].append(h)

        # Older databases have no frame_number on game_states: attach each state
        # to the last frame recorded at or before its timestamp.
        frame_ts = [f["timestamp"] for f in frames]
        states_by_frame: Dict[int, Dict[str, Any]] = {}
        for st in states:
            fn = st.get("frame_number")
            if fn is None:
                idx = max(0, bisect.bisect_right(frame_ts, st["timestamp"]) - 1)
                fn = frames[idx]["frame_number"]
            states_by_frame[fn] = {
                k: st.get(k)
                for k in ("player_health", "current_animation", "action_state", "level", "game_mode")
            }

        timeline: List[Dict[str, Any]] = []
        events: List[Dict[str, Any]] = []
        damage_events: List[Dict[str, Any]] = []
        prev_positions: Dict[str, Tuple[float, float]] = {}
        distance_traveled: Dict[str, float] = defaultdict(float)
        history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        entity_names: Dict[str, set] = defaultdict(set)
        colors: Dict[str, List[List[float]]] = defaultdict(list)
        last_hud: Dict[str, Optional[str]] = {}
        last_damage: Dict[str, int] = {}
        prev_health: Optional[int] = None
        prev_action: Optional[str] = None
        xs: List[float] = []

        for f in frames:
            fn = f["frame_number"]
            t_rel = round(f["timestamp"] - start_ts, 3)

            frame_entities: List[Dict[str, Any]] = []
            for e in by_frame.get(fn, []):
                pid = e.get("player_id") or e["entity_name"]
                x, y = e["x"], e["y"]
                app = e.get("appearance_signature") or {}
                entity_names[pid].add(e["entity_name"])
                if x is not None and y is not None:
                    if pid in prev_positions:
                        px, py = prev_positions[pid]
                        distance_traveled[pid] += math.hypot(x - px, y - py)
                    prev_positions[pid] = (x, y)
                    xs.append(x)
                    history[pid].append(
                        {"t": t_rel, "frame": fn, "x": x, "y": y,
                         "car": e.get("car"), "skin": e.get("skin")}
                    )
                    if app.get("dominant_color_bgr"):
                        colors[pid].append(app["dominant_color_bgr"])
                frame_entities.append(
                    {
                        "entity": e["entity_name"],
                        "player_id": pid,
                        "x": x,
                        "y": y,
                        "confidence": e.get("confidence"),
                        "method": e.get("method"),
                        "value": e.get("value"),
                        "car": e.get("car"),
                        "skin": e.get("skin"),
                        "appearance": app,
                    }
                )

            # HUD: carry the last known value forward so every frame shows the HUD state.
            for h in hud_by_frame.get(fn, []):
                zone, value = h["zone_name"], h["value"]
                last_hud[zone] = value
                if zone.lower().startswith("damage") and value is not None:
                    digits = "".join(ch for ch in str(value) if ch.isdigit())
                    if digits:
                        val = int(digits)
                        if last_damage.get(zone) != val:
                            damage_events.append({"t": t_rel, "frame": fn, "zone": zone, "value": val})
                            if zone in last_damage and val > last_damage[zone]:
                                events.append(
                                    {"t": t_rel, "frame": fn, "type": "damage_taken", "zone": zone,
                                     "from": last_damage[zone], "to": val}
                                )
                            last_damage[zone] = val
            frame_hud = [{"zone": z, "value": v} for z, v in last_hud.items()]

            gs = states_by_frame.get(fn, {})
            if gs:
                health = gs.get("player_health")
                if prev_health is not None and health is not None and health < prev_health:
                    events.append(
                        {"t": t_rel, "frame": fn, "type": "damage_taken", "from": prev_health,
                         "to": health, "level": gs.get("level")}
                    )
                if health is not None:
                    prev_health = health
                action = gs.get("action_state")
                if action and action != prev_action:
                    events.append({"t": t_rel, "frame": fn, "type": "action", "action": action})
                    prev_action = action

            timeline.append(
                {"t": t_rel, "frame": fn, "entities": frame_entities, "hud": frame_hud, "game_state": gs}
            )

        width = info.get("work_width") or (max(xs) if xs else 0)
        mid_x = width / 2 if width else 0
        players: Dict[str, Any] = {}
        for pid in sorted(entity_names):
            hist = history.get(pid, [])
            cars = [h["car"] for h in hist if h["car"]]
            skins = [h["skin"] for h in hist if h["skin"]]
            left = sum(1 for h in hist if h["x"] < mid_x)
            col = colors.get(pid)
            players[pid] = {
                "player_id": pid,
                "entity_names": sorted(entity_names[pid]),
                "car": max(set(cars), key=cars.count) if cars else None,
                "skin": max(set(skins), key=skins.count) if skins else None,
                "color_bgr": [round(sum(c[i] for c in col) / len(col), 1) for i in range(3)] if col else None,
                "distance_traveled_px": round(distance_traveled.get(pid, 0.0), 2),
                "frames_seen": len(hist),
                "seen_fraction": round(len(hist) / len(frames), 3),
                "first_seen_t": hist[0]["t"] if hist else None,
                "last_seen_t": hist[-1]["t"] if hist else None,
                "zone_time": {
                    "left": round(left / len(hist), 2) if hist else 0,
                    "right": round((len(hist) - left) / len(hist), 2) if hist else 0,
                },
                "appearance_samples": hist[:5],
            }

        replay.update(
            {
                "frame_size": [info.get("work_width") or None, info.get("work_height") or None],
                "players": players,
                "events": events,
                "damage_events": damage_events,
                "timeline": timeline,
            }
        )
        from middleware.analysis.feature_extractor import extract_features

        replay["stats"] = extract_features(replay)
        return replay

    def export_replay(
        self, replay: Dict[str, Any], output_path: str
    ) -> str:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            json.dump(replay, f, indent=2, default=str)
        return str(out)

    def replay_summary(self, replay: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "session_id": replay["session_id"],
            "duration": replay["duration_seconds"],
            "frames": replay["total_frames"],
            "game": replay.get("game"),
            "players": {
                pid: {
                    "car": p["car"],
                    "skin": p["skin"],
                    "distance_px": p["distance_traveled_px"],
                    "frames_seen": p["frames_seen"],
                    "zone_time": p["zone_time"],
                }
                for pid, p in replay["players"].items()
            },
            "stats": (replay.get("stats") or {}).get("players", {}),
            "event_count": len(replay["events"]),
            "damage_events": len(replay["damage_events"]),
        }
