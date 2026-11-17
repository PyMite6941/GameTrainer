"""
Dashboard data: match history, per-match stats, and career numbers per player.

Everything is read from the same gameplay.db the tracker writes, so the
dashboard can run while a match is being tracked (SQLite allows concurrent
readers). Replays are built once per finished session and cached as
<data>/replays/<session_id>.json (the same file run_session writes); a session
that is still being tracked is rebuilt at most every LIVE_REBUILD_S seconds.

Career numbers are per game and per player slot (p1, p2 ...), because speeds
are in screen pixels and only compare within one game. Every match stat also
gets a delta against that player's career average for the game - the
"better or worse than you usually play" view Leetify gives for CS2.
"""

from __future__ import annotations

import json
import re
import sqlite3
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional

from middleware.analysis.feature_extractor import extract_features
from middleware.analysis.replay_engine import ReplayEngine

LIVE_REBUILD_S = 5.0
SESSIONS_TTL_S = 2.0  # the session list is re-read from the database at most this often
REPLAY_CACHE = 3  # full replays kept in memory (a long match is tens of MB); summaries are always kept
LIVE_IDLE_S = 30.0  # a session with no ended_at and no frames for this long is treated as abandoned
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")

# Stats shown on the dashboard; "higher is better" is deliberately not claimed -
# whether more movement or closer spacing is good depends on the game.
STAT_KEYS = [
    "on_screen_pct",
    "avg_speed_px_s",
    "top_speed_px_s",
    "moving_pct",
    "screen_coverage_pct",
    "avg_opponent_distance_px",
    "close_quarters_pct",
]


class Store:
    def __init__(self, data_dir: str | Path = "./data", db_path: str | Path | None = None):
        self.data_dir = Path(data_dir)
        self.db_path = Path(db_path) if db_path else self.data_dir / "gameplay.db"
        self.replay_dir = self.data_dir / "replays"
        self._lock = threading.Lock()
        self._replays: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()  # session_id -> {"replay", "built_at"}
        self._summaries: Dict[str, Dict[str, Any]] = {}  # finished sessions only
        self._sessions: List[Dict[str, Any]] = []
        self._sessions_at = 0.0

    # ---------------------------------------------------------------- sessions
    def has_db(self) -> bool:
        return self.db_path.is_file()

    def _session_rows(self) -> Dict[str, Dict[str, Any]]:
        """Extra columns from the sessions table (profile, ended_at) keyed by id."""
        if not self.has_db():
            return {}
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        try:
            rows = conn.execute("SELECT session_id, profile, ended_at, started_at FROM sessions").fetchall()
        except sqlite3.OperationalError:
            rows = []
        finally:
            conn.close()
        return {sid: {"profile": prof, "ended_at": end, "started_at": start} for sid, prof, end, start in rows}

    def sessions(self) -> List[Dict[str, Any]]:
        """All sessions, newest first, with live/finished status."""
        if not self.has_db():
            return []
        with self._lock:
            if time.time() - self._sessions_at < SESSIONS_TTL_S:
                return self._sessions
        extra = self._session_rows()
        now = time.time()
        out = []
        for s in ReplayEngine(str(self.db_path)).load_sessions():
            row = extra.get(s["session_id"], {})
            live = (not s["session_id"].startswith("legacy_") and row.get("ended_at") is None
                    and now - (s.get("end") or 0) < LIVE_IDLE_S)
            out.append({**s, "profile": Path(row["profile"]).stem if row.get("profile") else None,
                        "ended_at": row.get("ended_at"), "live": live})
        out.sort(key=lambda s: s["start"] or 0, reverse=True)
        with self._lock:
            self._sessions, self._sessions_at = out, time.time()
        return out

    def session_ids(self) -> List[str]:
        return [s["session_id"] for s in self.sessions()]

    def _find(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not SESSION_ID_RE.match(session_id or ""):
            return None
        return next((s for s in self.sessions() if s["session_id"] == session_id), None)

    # ----------------------------------------------------------------- replays
    def replay(self, session_id: str) -> Optional[Dict[str, Any]]:
        """The session's replay (with stats), from cache when it is still valid."""
        sess = self._find(session_id)
        if sess is None:
            return None
        with self._lock:
            cached = self._replays.get(session_id)
            if cached and (not sess["live"] or time.time() - cached["built_at"] < LIVE_REBUILD_S):
                self._replays.move_to_end(session_id)
                return cached["replay"]
            path = self.replay_dir / f"{session_id}.json"
            replay = None
            if not sess["live"] and path.is_file():
                try:
                    replay = json.loads(path.read_text())
                    if replay.get("session_id") != session_id or replay.get("total_frames") != sess["frame_count"]:
                        replay = None  # stale (e.g. built while the match was still running)
                except (OSError, json.JSONDecodeError):
                    replay = None
            if replay is None:
                engine = ReplayEngine(str(self.db_path))
                replay = engine.build_replay(session_id)
                if not sess["live"]:
                    try:
                        engine.export_replay(replay, str(path))
                    except OSError:
                        pass  # read-only data dir: keep it in memory only
            if "stats" not in replay:
                replay["stats"] = extract_features(replay)
            self._replays[session_id] = {"replay": replay, "built_at": time.time()}
            self._replays.move_to_end(session_id)
            while len(self._replays) > REPLAY_CACHE:
                self._replays.popitem(last=False)
            return replay

    @staticmethod
    def final_hud(replay: Dict[str, Any]) -> Dict[str, Any]:
        """Last HUD value read in each zone (final lap, position, damage %, score ...)."""
        out: Dict[str, Any] = {}
        for fr in replay.get("timeline", []):
            for h in fr.get("hud") or []:
                if h.get("value") not in (None, ""):
                    out[h["zone"]] = h["value"]
        return out

    def summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """One match without its timeline: players, stats, events, final HUD."""
        cached = self._summaries.get(session_id)
        if cached is not None:
            return json.loads(json.dumps(cached))  # callers may add fields
        replay = self.replay(session_id)
        if replay is None:
            return None
        sess = self._find(session_id) or {}
        players = {}
        stats = (replay.get("stats") or {}).get("players", {})
        for pid, p in replay.get("players", {}).items():
            players[pid] = {
                "car": p.get("car"),
                "skin": p.get("skin"),
                "color_bgr": p.get("color_bgr"),
                "distance_px": p.get("distance_traveled_px"),
                "stats": stats.get(pid, {}),
            }
        summ = {
            "session_id": session_id,
            "game": replay.get("game"),
            "console": replay.get("console"),
            "profile": sess.get("profile"),
            "live": sess.get("live", False),
            "start": sess.get("start"),
            "duration_seconds": replay.get("duration_seconds"),
            "frames": replay.get("total_frames"),
            "frame_size": replay.get("frame_size"),
            "players": players,
            "match": (replay.get("stats") or {}).get("match", {}),
            "events": replay.get("events", [])[:500],
            "final_hud": self.final_hud(replay),
        }
        if not summ["live"]:
            self._summaries[session_id] = json.loads(json.dumps(summ))
        return summ

    # ------------------------------------------------------------------ career
    def career(self, game: Optional[str] = None, limit: int = 200) -> Dict[str, Any]:
        """Averages per (game, player slot) over finished matches, plus a trend series."""
        groups: Dict[str, Dict[str, Any]] = {}
        for s in self.sessions()[:limit]:
            if s["live"] or (game and s.get("game") != game):
                continue
            summ = self.summary(s["session_id"])
            if not summ:
                continue
            g = summ.get("game") or "Unknown game"
            for pid, p in summ["players"].items():
                key = f"{g}::{pid}"
                grp = groups.setdefault(key, {"game": g, "player_id": pid, "matches": 0, "seconds": 0.0,
                                              "looks": {}, "trend": [], "_sums": {}, "_counts": {}})
                grp["matches"] += 1
                grp["seconds"] += summ.get("duration_seconds") or 0
                look = p.get("car") or p.get("skin")
                if look:
                    grp["looks"][look] = grp["looks"].get(look, 0) + 1
                point = {"session_id": s["session_id"], "start": s["start"]}
                for k in STAT_KEYS:
                    v = p["stats"].get(k)
                    point[k] = v
                    if isinstance(v, (int, float)):
                        grp["_sums"][k] = grp["_sums"].get(k, 0.0) + v
                        grp["_counts"][k] = grp["_counts"].get(k, 0) + 1
                grp["trend"].append(point)
        players = []
        for grp in groups.values():
            sums, counts = grp.pop("_sums"), grp.pop("_counts")
            grp["averages"] = {k: round(sums[k] / counts[k], 1) for k in sums}
            grp["usual_look"] = max(grp["looks"], key=grp["looks"].get) if grp["looks"] else None
            grp["trend"].sort(key=lambda p: p["start"] or 0)
            grp["seconds"] = round(grp["seconds"], 1)
            players.append(grp)
        players.sort(key=lambda g: (g["game"], g["player_id"]))
        return {"players": players}

    def summary_with_deltas(self, session_id: str) -> Optional[Dict[str, Any]]:
        """A match summary where each stat also shows its difference from the
        player's career average for that game (the average includes this match)."""
        summ = self.summary(session_id)
        if summ is None:
            return None
        career = {g["player_id"]: g for g in self.career(game=summ.get("game"))["players"]}
        for pid, p in summ["players"].items():
            avg = career.get(pid, {}).get("averages", {})
            p["career_matches"] = career.get(pid, {}).get("matches", 0)
            p["vs_average"] = {
                k: round(p["stats"][k] - avg[k], 1)
                for k in STAT_KEYS
                if isinstance(p["stats"].get(k), (int, float)) and k in avg
            }
        return summ

    def overview(self) -> Dict[str, Any]:
        sessions = self.sessions()
        games: Dict[str, int] = {}
        for s in sessions:
            games[s.get("game") or "Unknown game"] = games.get(s.get("game") or "Unknown game", 0) + 1
        return {
            "matches": len(sessions),
            "live": [s["session_id"] for s in sessions if s["live"]],
            "seconds_tracked": round(sum(s.get("duration") or 0 for s in sessions), 1),
            "games": games,
            "latest": sessions[0]["session_id"] if sessions else None,
        }
