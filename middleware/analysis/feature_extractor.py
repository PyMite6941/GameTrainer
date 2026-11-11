"""
Feature extraction: Leetify-style per-player stats from a replay's data points.

Works on the replay dict built by ReplayEngine (no video). For each player:

  avg_speed_px_s      mean speed while on screen
  top_speed_px_s      95th-percentile speed (ignores single-frame tracking jumps)
  moving_pct          share of time moving faster than MOVING_PX_S
  screen_coverage_pct share of an 8x6 grid over the frame the player visited
  on_screen_pct       share of frames the player was detected in
  avg_opponent_distance_px / close_quarters_pct
                      distance to the nearest other player, and how often it is
                      under 15% of the frame diagonal (engagement proxy)

Speeds are in working-frame pixels per second, so compare players within the
same game, not across games.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

MOVING_PX_S = 30.0
GRID_COLS, GRID_ROWS = 8, 6
CLOSE_FRACTION = 0.15


def _percentile(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    vals = sorted(values)
    k = (len(vals) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return vals[lo] if lo == hi else vals[lo] + (vals[hi] - vals[lo]) * (k - lo)


class FeatureExtractor:
    def __init__(self, replay: Dict[str, Any]):
        self.replay = replay
        self.timeline: List[Dict[str, Any]] = replay.get("timeline", [])
        self.tracks = self._tracks()
        fw, fh = (replay.get("frame_size") or [None, None])[:2]
        if not fw or not fh:
            xs = [x for tr in self.tracks.values() for _, x, _ in tr]
            ys = [y for tr in self.tracks.values() for _, _, y in tr]
            fw, fh = (max(xs) if xs else 1), (max(ys) if ys else 1)
        self.frame_w, self.frame_h = float(fw), float(fh)

    def _tracks(self) -> Dict[str, List[Tuple[float, float, float]]]:
        tracks: Dict[str, List[Tuple[float, float, float]]] = {}
        for fr in self.timeline:
            for e in fr.get("entities", []):
                if e.get("x") is None or e.get("y") is None:
                    continue
                pid = e.get("player_id") or e.get("entity")
                tracks.setdefault(pid, []).append((float(fr.get("t", 0.0)), float(e["x"]), float(e["y"])))
        return tracks

    def player_stats(self, pid: str) -> Dict[str, Any]:
        track = self.tracks.get(pid, [])
        speeds: List[float] = []
        moving_time = total_time = 0.0
        for (t0, x0, y0), (t1, x1, y1) in zip(track, track[1:]):
            dt = t1 - t0
            if dt <= 0 or dt > 1.0:  # skip gaps where the player was off screen
                continue
            v = math.hypot(x1 - x0, y1 - y0) / dt
            speeds.append(v)
            total_time += dt
            if v >= MOVING_PX_S:
                moving_time += dt

        cells = {
            (min(GRID_COLS - 1, int(x / self.frame_w * GRID_COLS)), min(GRID_ROWS - 1, int(y / self.frame_h * GRID_ROWS)))
            for _, x, y in track
        }

        # Nearest other player, frame by frame
        diag = math.hypot(self.frame_w, self.frame_h)
        dists: List[float] = []
        for fr in self.timeline:
            pos = {}
            for e in fr.get("entities", []):
                if e.get("x") is not None and e.get("y") is not None:
                    pos[e.get("player_id") or e.get("entity")] = (e["x"], e["y"])
            if pid in pos and len(pos) > 1:
                me = pos[pid]
                dists.append(min(math.hypot(me[0] - p[0], me[1] - p[1]) for k, p in pos.items() if k != pid))

        n_frames = len(self.timeline) or 1
        return {
            "player_id": pid,
            "frames_tracked": len(track),
            "on_screen_pct": round(100 * len(track) / n_frames, 1),
            "avg_speed_px_s": round(sum(speeds) / len(speeds), 1) if speeds else 0.0,
            "top_speed_px_s": round(_percentile(speeds, 0.95), 1),
            "moving_pct": round(100 * moving_time / total_time, 1) if total_time else 0.0,
            "screen_coverage_pct": round(100 * len(cells) / (GRID_COLS * GRID_ROWS), 1),
            "avg_opponent_distance_px": round(sum(dists) / len(dists), 1) if dists else None,
            "close_quarters_pct": round(100 * sum(1 for d in dists if d < CLOSE_FRACTION * diag) / len(dists), 1) if dists else None,
        }

    def extract(self) -> Dict[str, Any]:
        players = {pid: self.player_stats(pid) for pid in sorted(self.tracks)}
        return {
            "players": players,
            "match": {
                "duration_seconds": self.replay.get("duration_seconds", 0),
                "frames": len(self.timeline),
                "events": len(self.replay.get("events", [])),
                "most_active": max(players, key=lambda p: players[p]["avg_speed_px_s"]) if players else None,
            },
        }


def extract_features(replay: Dict[str, Any]) -> Dict[str, Any]:
    return FeatureExtractor(replay).extract()


def format_stats(stats: Dict[str, Any], replay: Optional[Dict[str, Any]] = None) -> str:
    """Plain-text scoreboard for the terminal."""
    lines = []
    if replay:
        lines.append(f"{replay.get('game') or 'Match'}  session {replay.get('session_id')}  "
                     f"{replay.get('duration_seconds', 0):.1f}s, {len(replay.get('timeline', []))} frames")
    lines.append(f"{'player':12s} {'on screen':>9s} {'avg speed':>10s} {'top speed':>10s} {'moving':>7s} "
                 f"{'coverage':>9s} {'opp dist':>9s} {'close':>6s}")
    for pid, p in stats["players"].items():
        opp = "-" if p["avg_opponent_distance_px"] is None else f"{p['avg_opponent_distance_px']:.0f}px"
        close = "-" if p["close_quarters_pct"] is None else f"{p['close_quarters_pct']:.0f}%"
        lines.append(
            f"{pid:12s} {p['on_screen_pct']:8.0f}% {p['avg_speed_px_s']:7.0f}px/s {p['top_speed_px_s']:7.0f}px/s "
            f"{p['moving_pct']:6.0f}% {p['screen_coverage_pct']:8.0f}% {opp:>9s} {close:>6s}"
        )
    return "\n".join(lines)
