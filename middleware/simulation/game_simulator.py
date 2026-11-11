"""
Game simulator: plays a replay back as a continuous stream of game states.

The tracker records positions only on processed frames (e.g. 30 per second, with
gaps when a player is off screen). GameSimulator turns that into a state at
*any* time t by interpolating each player's position between neighbouring
samples, so playback is smooth at any frame rate and speed:

    sim = GameSimulator.from_file("data/replays/replay.json")
    sim.state_at(12.5)            # {"t": 12.5, "players": {"p1": {...}, ...}, "hud": [...]}
    for state in sim.play(fps=60):   # fixed-rate stream over the whole match
        ...

A player missing for longer than max_gap seconds is reported as off screen
instead of being interpolated across the gap.
"""

from __future__ import annotations

import bisect
import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union


class GameSimulator:
    def __init__(self, replay: Dict[str, Any], max_gap: float = 0.5):
        self.replay = replay
        self.max_gap = max_gap
        self.timeline: List[Dict[str, Any]] = replay.get("timeline", [])
        self.times = [fr.get("t", 0.0) for fr in self.timeline]
        self.duration = self.times[-1] if self.times else 0.0
        # Per-player samples: times and entity records
        self._samples: Dict[str, Tuple[List[float], List[Dict[str, Any]]]] = {}
        for fr in self.timeline:
            for e in fr.get("entities", []):
                if e.get("x") is None or e.get("y") is None:
                    continue
                pid = e.get("player_id") or e.get("entity")
                ts, recs = self._samples.setdefault(pid, ([], []))
                ts.append(fr.get("t", 0.0))
                recs.append(e)

    @classmethod
    def from_file(cls, path: Union[str, Path], **kw) -> "GameSimulator":
        with open(path) as f:
            return cls(json.load(f), **kw)

    @property
    def players(self) -> List[str]:
        return sorted(self._samples)

    def player_at(self, pid: str, t: float) -> Optional[Dict[str, Any]]:
        """Interpolated record for one player at time t, or None if off screen."""
        ts, recs = self._samples.get(pid, ([], []))
        if not ts:
            return None
        i = bisect.bisect_right(ts, t)
        if i == 0:
            return dict(recs[0]) if ts[0] - t <= self.max_gap else None
        if i == len(ts):
            return dict(recs[-1]) if t - ts[-1] <= self.max_gap else None
        t0, t1 = ts[i - 1], ts[i]
        a, b = recs[i - 1], recs[i]
        if t1 - t0 > self.max_gap:
            # Gap in tracking: hold the last sample briefly, then report off screen.
            return dict(a) if t - t0 <= self.max_gap else None
        f = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
        out = dict(a)
        out["x"] = a["x"] + (b["x"] - a["x"]) * f
        out["y"] = a["y"] + (b["y"] - a["y"]) * f
        out["interpolated"] = 0.0 < f < 1.0
        return out

    def state_at(self, t: float) -> Dict[str, Any]:
        t = max(0.0, min(self.duration, t))
        idx = max(0, bisect.bisect_right(self.times, t) - 1)
        frame = self.timeline[idx] if self.timeline else {}
        players = {}
        for pid in self.players:
            rec = self.player_at(pid, t)
            if rec is not None:
                players[pid] = rec
        return {
            "t": t,
            "frame": frame.get("frame"),
            "players": players,
            "hud": frame.get("hud", []),
            "game_state": frame.get("game_state", {}),
        }

    def play(self, fps: float = 30.0, speed: float = 1.0) -> Iterator[Dict[str, Any]]:
        """States at a fixed rate from start to end (speed 2.0 = twice as fast)."""
        if not self.timeline:
            return
        step = speed / fps
        t = 0.0
        while t < self.duration:
            yield self.state_at(t)
            t += step
        yield self.state_at(self.duration)


Game_Simulator = GameSimulator
