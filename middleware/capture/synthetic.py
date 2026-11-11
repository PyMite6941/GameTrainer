"""Synthetic test match for running GameTrainer without a capture card.

Draws a 1280x720 "match": a green player and a red opponent moving around a
dark stage, plus an orange sprite. The colors match the Smash Bros. profile
(p1 green, p2 red), so any color-based profile tuned to those colors - and the
generic motion profile - can be exercised end to end.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import cv2
import numpy as np

WIDTH, HEIGHT = 1280, 720
PLAYER_BGR = (0, 200, 0)
OPPONENT_BGR = (0, 0, 200)
SPRITE_BGR = (0, 140, 255)


def player_pos(i: int, frames: int):
    px = 100 + int(900 * (i / max(frames - 1, 1)))
    py = 360 + int(60 * np.sin(i * 0.3))
    return px, py


def opponent_pos(i: int, frames: int):
    ox = 1180 - int(900 * (i / max(frames - 1, 1)))
    oy = 360 + int(60 * np.cos(i * 0.3))
    return ox, oy


def make_sprite(path: Union[str, Path]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sprite = np.zeros((40, 40, 3), np.uint8)
    sprite[:] = SPRITE_BGR
    sprite[10:30, 10:30] = (255, 255, 255)  # give the template some structure
    cv2.imwrite(str(path), sprite)
    return path


def make_video(path: Union[str, Path], frames: int = 120, fps: int = 30) -> Path:
    """Write the synthetic match video and return its path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (WIDTH, HEIGHT))
    if not writer.isOpened():
        raise RuntimeError(f"OpenCV could not write {path} (mp4v codec unavailable?)")
    for i in range(frames):
        frame = np.full((HEIGHT, WIDTH, 3), (30, 40, 50), np.uint8)
        cv2.circle(frame, player_pos(i, frames), 22, PLAYER_BGR, -1)
        cv2.circle(frame, opponent_pos(i, frames), 22, OPPONENT_BGR, -1)
        sx = 620 + int(40 * np.sin(i * 0.2))
        sy = 100 + (i * 4) % 560
        frame[sy : sy + 40, sx : sx + 40] = SPRITE_BGR
        frame[sy + 10 : sy + 30, sx + 10 : sx + 30] = (255, 255, 255)
        writer.write(frame)
    writer.release()
    return path
