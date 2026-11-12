"""
Monitor mode: the host shows the console's picture on its own screen.

Wiring for monitor mode: console -> capture card -> host USB, host HDMI Out ->
TV. Every captured frame (not just the ones being analysed) is shown full
screen at the card's full resolution, so the TV works as the game screen while
GameTrainer records data points in the background.

Passthrough wiring (card HDMI Out -> TV) has no added lag and is better for
competitive play; monitor mode adds roughly 1-3 frames, depending on the host.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

WINDOW = "GameTrainer monitor (Esc or q to stop)"


class LiveMonitor:
    def __init__(self, fullscreen: bool = True, show_recording_dot: bool = True):
        self.fullscreen = fullscreen
        self.show_recording_dot = show_recording_dot
        self.closed = False
        self._opened = False
        self.frames_shown = 0

    def _open(self) -> None:
        import cv2

        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
        if self.fullscreen:
            cv2.setWindowProperty(WINDOW, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        self._opened = True

    def show(self, frame: Optional[np.ndarray]) -> bool:
        """Display one frame. Returns False once the player pressed Esc/q or closed the window."""
        if self.closed or frame is None:
            return not self.closed
        import cv2

        if not self._opened:
            self._open()
        if self.show_recording_dot:
            frame = frame.copy()
            h, w = frame.shape[:2]
            r = max(4, w // 240)
            cv2.circle(frame, (w - 3 * r, 3 * r), r, (0, 0, 255), -1, cv2.LINE_AA)
        cv2.imshow(WINDOW, frame)
        self.frames_shown += 1
        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q")):
            self.closed = True
        else:
            try:
                if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                    self.closed = True
            except Exception:
                pass
        return not self.closed

    def close(self) -> None:
        if self._opened:
            import cv2

            try:
                cv2.destroyWindow(WINDOW)
                cv2.waitKey(1)
            except Exception:
                pass
        self._opened = False
        self.closed = True
