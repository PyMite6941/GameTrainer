"""
Replay Viewer - renders a ReplayEngine replay.json entirely from data points.

No source video is required. Each tracked player is drawn as a marker in the
color actually measured from the capture (their car / skin / body color), with
a fading movement trail, a timeline scrubber with event markers, play/pause,
speed control, and a per-player stats panel.

Controls: Space play/pause, Left/Right step, Shift+Left/Right jump 5 s,
Home/End, Up/Down speed, T toggle trails, click/drag the timeline to scrub,
Esc/Q quit.

Usage:
    python track_game.py ./data/replays/replay.json
    python -m middleware.simulation.replay_viewer ./data/replays/replay.json
"""

from __future__ import annotations

import bisect
import colorsys
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pygame

from middleware.analysis.replay_engine import ReplayEngine

Color = Tuple[int, int, int]

NAMED_COLORS: Dict[str, Color] = {
    "red": (230, 60, 60),
    "orange": (255, 140, 0),
    "yellow": (240, 210, 40),
    "green": (60, 200, 80),
    "cyan": (40, 210, 220),
    "blue": (60, 110, 255),
    "purple": (170, 80, 255),
    "pink": (255, 110, 190),
    "white": (235, 235, 235),
    "gray": (150, 150, 150),
    "black": (70, 70, 70),
}

PANEL_W = 300
MARGIN = 40
TOP = 50
BOTTOM = 120
TRAIL_SECONDS = 2.0


def label_color(label: Optional[str]) -> Optional[Color]:
    """Color for a car/skin label such as 'green_body' or 'red'."""
    if not label:
        return None
    base = str(label).lower().replace("_body", "")
    return NAMED_COLORS.get(base)


def stable_color(key: str) -> Color:
    """Deterministic distinct color for labels that don't name a color."""
    h = (sum(ord(ch) * (i + 1) for i, ch in enumerate(key)) % 360) / 360.0
    r, g, b = colorsys.hsv_to_rgb(h, 0.65, 0.95)
    return int(r * 255), int(g * 255), int(b * 255)


def appearance_color(entry: Dict[str, Any]) -> Color:
    """The color a player actually looked like in the capture."""
    app = entry.get("appearance") or {}
    bgr = app.get("dominant_color_bgr") or entry.get("color_bgr")
    if bgr:
        return int(bgr[2]), int(bgr[1]), int(bgr[0])
    for key in ("skin", "car"):
        c = label_color(entry.get(key))
        if c:
            return c
    return stable_color(str(entry.get("player_id") or entry.get("entity") or "?"))


class ReplayViewer:
    def __init__(self, replay_path: str, width: int = 1280, height: int = 720):
        self.replay_path = Path(replay_path)
        with open(self.replay_path, "r") as f:
            self.replay = json.load(f)

        self.width = width
        self.height = height
        self.timeline: List[Dict[str, Any]] = self.replay.get("timeline", [])
        self.players: Dict[str, Any] = self.replay.get("players", {})
        self.times: List[float] = [fr.get("t", i / 30.0) for i, fr in enumerate(self.timeline)]
        self.duration = self.times[-1] if self.times else 0.0
        self.events: List[Dict[str, Any]] = self.replay.get("events", [])
        self.stats: Dict[str, Any] = (self.replay.get("stats") or {}).get("players", {})

        self.index = 0
        self.playhead = 0.0  # seconds into the replay
        self.playing = False
        self.speed = 1.0
        self.show_trails = True
        self.dragging = False

        self.font = None
        self.small_font = None
        self.screen = None
        self.clock = None

        self._compute_bounds()

    # ------------------------------------------------------------ geometry
    def _compute_bounds(self) -> None:
        fw, fh = (self.replay.get("frame_size") or [None, None])[:2]
        if fw and fh:
            self.x_min, self.x_max, self.y_min, self.y_max = 0.0, float(fw), 0.0, float(fh)
            return
        xs = [e["x"] for fr in self.timeline for e in fr.get("entities", []) if e.get("x") is not None]
        ys = [e["y"] for fr in self.timeline for e in fr.get("entities", []) if e.get("y") is not None]
        if not xs:
            self.x_min, self.x_max, self.y_min, self.y_max = 0.0, 1280.0, 0.0, 720.0
            return
        mx = max(20.0, (max(xs) - min(xs)) * 0.1)
        my = max(20.0, (max(ys) - min(ys)) * 0.1)
        self.x_min, self.x_max = min(xs) - mx, max(xs) + mx
        self.y_min, self.y_max = min(ys) - my, max(ys) + my

    def _arena(self) -> pygame.Rect:
        """Largest rect with the capture's aspect ratio left of the stats panel."""
        avail_w = self.width - PANEL_W - 2 * MARGIN
        avail_h = self.height - TOP - BOTTOM
        aspect = (self.x_max - self.x_min) / max(1e-6, self.y_max - self.y_min)
        w = min(avail_w, int(avail_h * aspect))
        h = int(w / aspect) if aspect else avail_h
        return pygame.Rect(MARGIN + (avail_w - w) // 2, TOP + (avail_h - h) // 2, w, h)

    def _to_screen(self, x: Optional[float], y: Optional[float], arena: pygame.Rect) -> Optional[Tuple[int, int]]:
        if x is None or y is None:
            return None
        nx = (x - self.x_min) / max(1e-6, self.x_max - self.x_min)
        ny = (y - self.y_min) / max(1e-6, self.y_max - self.y_min)
        return arena.x + int(nx * arena.w), arena.y + int(ny * arena.h)

    def _bar(self) -> pygame.Rect:
        return pygame.Rect(MARGIN, self.height - 32, self.width - PANEL_W - 2 * MARGIN, 8)

    # ------------------------------------------------------------ playback
    def seek(self, t: float) -> None:
        self.playhead = max(0.0, min(self.duration, t))
        self.index = max(0, bisect.bisect_right(self.times, self.playhead) - 1)

    def step(self, delta: int) -> None:
        if not self.timeline:
            return
        self.index = max(0, min(len(self.timeline) - 1, self.index + delta))
        self.playhead = self.times[self.index]

    def update(self, dt: float) -> None:
        if self.playing and self.timeline:
            self.seek(self.playhead + dt * self.speed)
            if self.playhead >= self.duration:
                self.playing = False

    # ------------------------------------------------------------ drawing
    def init_display(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((self.width, self.height))
        title = self.replay.get("game") or "GameTrainer"
        pygame.display.set_caption(f"{title} - data-point replay (no video)")
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 19)
        self.clock = pygame.time.Clock()

    def _text(self, text: str, pos: Tuple[int, int], color: Color = (230, 230, 230), small: bool = True) -> None:
        font = self.small_font if small else self.font
        self.screen.blit(font.render(text, True, color), pos)

    def draw_frame(self) -> None:
        self.screen.fill((24, 24, 30))
        arena = self._arena()
        pygame.draw.rect(self.screen, (34, 36, 44), arena)
        pygame.draw.rect(self.screen, (70, 72, 84), arena, 1)
        frame = self.timeline[self.index] if self.timeline else {}

        # Trails: each player's recent path
        if self.show_trails and self.timeline:
            t_now = self.times[self.index]
            first = bisect.bisect_left(self.times, t_now - TRAIL_SECONDS)
            paths: Dict[str, List[Tuple[Tuple[int, int], Color]]] = {}
            for fr in self.timeline[first : self.index + 1]:
                for e in fr.get("entities", []):
                    p = self._to_screen(e.get("x"), e.get("y"), arena)
                    if p:
                        paths.setdefault(e.get("player_id") or e["entity"], []).append((p, appearance_color(e)))
            for pts in paths.values():
                for i in range(1, len(pts)):
                    fade = i / len(pts)
                    c = tuple(int(24 + (v - 24) * fade * 0.8) for v in pts[i][1])
                    pygame.draw.line(self.screen, c, pts[i - 1][0], pts[i][0], 3)

        # Players at the playhead
        for e in frame.get("entities", []):
            pos = self._to_screen(e.get("x"), e.get("y"), arena)
            if not pos:
                continue
            color = appearance_color(e)
            pygame.draw.circle(self.screen, color, pos, 13)
            pygame.draw.circle(self.screen, (255, 255, 255), pos, 13, 2)
            self._text(str(e.get("player_id") or e["entity"]), (pos[0] + 16, pos[1] - 8))

        # HUD values and game state under the arena
        y = self.height - BOTTOM + 20
        hud = "   ".join(f'{h["zone"]}: {h["value"]}' for h in frame.get("hud", []) if h.get("value") is not None)
        if hud:
            self._text(hud, (MARGIN, y), (200, 220, 255))
            y += 22
        gs = frame.get("game_state") or {}
        state = "   ".join(f"{k}: {v}" for k, v in gs.items() if v is not None)
        if state:
            self._text(state, (MARGIN, y), (180, 255, 180))

        self._draw_panel()
        self._draw_timeline()

        status = (
            f"{self.replay.get('game') or 'replay'}  |  t={self.playhead:6.2f}s / {self.duration:.2f}s  |  "
            f"frame {frame.get('frame', self.index)}  |  {'PLAYING' if self.playing else 'PAUSED'}  |  "
            f"{self.speed:.2g}x"
        )
        self._text(status, (MARGIN, 16), (255, 230, 90), small=False)
        pygame.display.flip()

    def _draw_panel(self) -> None:
        px = self.width - PANEL_W
        pygame.draw.rect(self.screen, (36, 38, 48), (px, 0, PANEL_W, self.height))
        self._text("Players", (px + 16, 16), (255, 255, 255), small=False)
        yy = 50
        for pid, p in self.players.items():
            color = appearance_color({"color_bgr": p.get("color_bgr"), "car": p.get("car"),
                                      "skin": p.get("skin"), "player_id": pid})
            pygame.draw.circle(self.screen, color, (px + 24, yy + 8), 9)
            self._text(str(pid), (px + 42, yy), (255, 255, 255))
            yy += 20
            st = self.stats.get(pid, {})
            lines = [
                f"car: {p.get('car')}   skin: {p.get('skin')}",
                f"distance: {p.get('distance_traveled_px', 0):.0f}px   "
                f"on screen: {100 * (p.get('seen_fraction') or 0):.0f}%",
            ]
            if st:
                lines.append(f"speed: {st.get('avg_speed_px_s', 0):.0f} avg / {st.get('top_speed_px_s', 0):.0f} top px/s")
                close = st.get("close_quarters_pct")
                lines.append(f"moving: {st.get('moving_pct', 0):.0f}%   coverage: {st.get('screen_coverage_pct', 0):.0f}%"
                             + (f"   close: {close:.0f}%" if close is not None else ""))
            for line in lines:
                self._text(line, (px + 42, yy), (170, 175, 190))
                yy += 18
            yy += 12
            if yy > self.height - 140:
                break
        yy = self.height - 120
        self._text(f"Events: {len(self.events)}", (px + 16, yy), (255, 255, 255))
        for line in ("Space play/pause  Up/Down speed", "Left/Right step  Shift: 5s jump",
                     "T trails  Home/End  Esc quit"):
            yy += 20
            self._text(line, (px + 16, yy), (140, 145, 160))

    def _draw_timeline(self) -> None:
        bar = self._bar()
        pygame.draw.rect(self.screen, (70, 72, 84), bar, border_radius=4)
        if self.duration > 0:
            for ev in self.events:
                ex = bar.x + int(ev.get("t", 0) / self.duration * bar.w)
                pygame.draw.line(self.screen, (255, 120, 90), (ex, bar.y - 6), (ex, bar.bottom + 6), 2)
            frac = self.playhead / self.duration
            done = pygame.Rect(bar.x, bar.y, int(frac * bar.w), bar.h)
            pygame.draw.rect(self.screen, (90, 190, 255), done, border_radius=4)
            pygame.draw.circle(self.screen, (255, 255, 255), (bar.x + int(frac * bar.w), bar.centery), 8)

    # ------------------------------------------------------------ loop
    def _scrub_to(self, mx: int) -> None:
        bar = self._bar()
        frac = (mx - bar.x) / max(1, bar.w)
        self.seek(max(0.0, min(1.0, frac)) * self.duration)

    def handle_event(self, event: "pygame.event.Event") -> bool:
        """Returns False when the viewer should close."""
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            shift = event.mod & pygame.KMOD_SHIFT
            if event.key in (pygame.K_ESCAPE, pygame.K_q):
                return False
            if event.key == pygame.K_SPACE:
                if not self.playing and self.playhead >= self.duration:
                    self.seek(0.0)
                self.playing = not self.playing
            elif event.key == pygame.K_RIGHT:
                self.seek(self.playhead + 5) if shift else self.step(1)
            elif event.key == pygame.K_LEFT:
                self.seek(self.playhead - 5) if shift else self.step(-1)
            elif event.key == pygame.K_UP:
                self.speed = min(8.0, self.speed * 2)
            elif event.key == pygame.K_DOWN:
                self.speed = max(0.125, self.speed / 2)
            elif event.key == pygame.K_HOME:
                self.seek(0.0)
            elif event.key == pygame.K_END:
                self.seek(self.duration)
            elif event.key == pygame.K_t:
                self.show_trails = not self.show_trails
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._bar().inflate(0, 30).collidepoint(event.pos):
                self.dragging = True
                self._scrub_to(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._scrub_to(event.pos[0])
        return True

    def run(self, max_seconds: Optional[float] = None, autoplay: bool = False) -> None:
        """Open the window. max_seconds closes it automatically (used for tests)."""
        self.init_display()
        self.playing = autoplay
        opened = time.time()
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                running = self.handle_event(event) and running
            self.update(dt)
            self.draw_frame()
            if max_seconds is not None and time.time() - opened >= max_seconds:
                running = False
        pygame.quit()

    def save_snapshot(self, path: str) -> str:
        """Render the current frame to an image (no window needed with SDL_VIDEODRIVER=dummy)."""
        if self.screen is None:
            self.init_display()
        self.draw_frame()
        pygame.image.save(self.screen, path)
        return path


def build_replay_first(
    db_path: str = "./data/gameplay.db",
    session_id: Optional[str] = None,
    output: str = "./data/replays/replay.json",
) -> str:
    """Build a replay from a DB (latest session by default) and save it."""
    engine = ReplayEngine(db_path)
    if session_id is None:
        session_id = engine.latest_session_id()
        if session_id is None:
            raise RuntimeError("No sessions found in database.")
    return engine.export_replay(engine.build_replay(session_id), output)


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="View a GameTrainer data-point replay")
    p.add_argument("replay", nargs="?", help="replay.json to view (omit to build one from --db)")
    p.add_argument("--db", default="./data/gameplay.db")
    p.add_argument("--session", default=None)
    p.add_argument("--output", default="./data/replays/replay.json")
    p.add_argument("--build", action="store_true", help="only build the replay, don't open it")
    args = p.parse_args(argv)

    replay_path = args.replay
    if args.build or replay_path is None:
        replay_path = build_replay_first(args.db, args.session, args.output)
        print(f"Replay built: {replay_path}")
        if args.build:
            return 0
    ReplayViewer(replay_path).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
