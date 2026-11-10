"""
HDMI capture: the console's picture, as frames on the laptop.

Wiring (any console): console HDMI Out -> capture card HDMI In; card HDMI Out
-> TV (passthrough, so the TV stays the monitor); card USB -> laptop. The card
is a UVC camera to the operating system. HdmiCapture opens it, asks for the
configured mode (default 1920x1080 @ 60 in MJPG, which fits through USB),
downscales to the working size, and notices a black picture - usually HDCP
left on (PS4/PS5) or the console not outputting.

Works the same on a video file path, which is how the test match is replayed.
"""

from __future__ import annotations

import sys
import time
from typing import Any, Dict, Optional, Tuple, Union

import cv2
import numpy as np

Device = Union[int, str]


def open_capture(device: Device) -> "cv2.VideoCapture":
    """Open a capture card by index (V4L2 on Linux, to skip non-camera devices) or a video file."""
    if isinstance(device, int) and sys.platform.startswith("linux"):
        # Capture cards are V4L2 devices; don't let OpenCV fall back to FFmpeg probing.
        return cv2.VideoCapture(device, cv2.CAP_V4L2)
    if isinstance(device, int) and sys.platform == "win32":
        cap = cv2.VideoCapture(device, cv2.CAP_DSHOW)  # DirectShow opens UVC cards fastest
        if cap.isOpened():
            return cap
        cap.release()
    return cv2.VideoCapture(device)


def camera_backends() -> list:
    """Names of the camera backends this OpenCV build has (V4L2, DSHOW, MSMF, AVFOUNDATION...)."""
    try:
        from cv2 import videoio_registry

        return [videoio_registry.getBackendName(b) for b in videoio_registry.getCameraBackends()]
    except Exception:
        return []


class HdmiCapture:
    """A capture card (or video file) delivering working-size BGR frames."""

    def __init__(
        self,
        device: Device = 0,
        width: Optional[int] = 1920,
        height: Optional[int] = 1080,
        fps: Optional[int] = 60,
        fourcc: Optional[str] = "MJPG",
        downscale_width: Optional[int] = 1280,
        black_seconds: float = 3.0,
    ):
        self.device = device
        self.requested = {"width": width, "height": height, "fps": fps, "fourcc": fourcc}
        self.downscale_width = downscale_width
        self.cap: Optional[cv2.VideoCapture] = None
        self.source_width = 0
        self.source_height = 0
        self.fps = 30
        self.scale = 1.0
        self.work_w = 0
        self.work_h = 0
        self.frames_read = 0
        self.black_seconds = black_seconds
        self._black_run = 0
        self.started_at = 0.0
        self.last_timestamp = 0.0  # capture time of the last frame read

    @classmethod
    def from_config(cls, device: Device, capture_cfg: Dict[str, Any], downscale_width: Optional[int] = None) -> "HdmiCapture":
        return cls(
            device=device,
            width=capture_cfg.get("width", 1920),
            height=capture_cfg.get("height", 1080),
            fps=capture_cfg.get("fps", 60),
            fourcc=capture_cfg.get("fourcc", "MJPG"),
            downscale_width=downscale_width or capture_cfg.get("downscale_width", 1280),
        )

    @staticmethod
    def is_supported() -> bool:
        """True if this OpenCV build can open cameras at all."""
        return bool(camera_backends()) or hasattr(cv2, "VideoCapture")

    @property
    def is_file(self) -> bool:
        return not isinstance(self.device, int)

    def open(self) -> Tuple[int, int, int]:
        """Open the device and return (fps, working width, working height)."""
        self.cap = open_capture(self.device)
        if not self.cap.isOpened():
            self.cap = None
            raise RuntimeError(f"Cannot open video device {self.device}")
        if not self.is_file:
            req = self.requested
            if req.get("fourcc"):
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*req["fourcc"]))
            for prop, key in (
                (cv2.CAP_PROP_FRAME_WIDTH, "width"),
                (cv2.CAP_PROP_FRAME_HEIGHT, "height"),
                (cv2.CAP_PROP_FPS, "fps"),
            ):
                if req.get(key):
                    self.cap.set(prop, int(req[key]))
        self.source_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.source_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = int(round(self.cap.get(cv2.CAP_PROP_FPS))) or 30
        if self.downscale_width and self.source_width > self.downscale_width:
            self.scale = self.downscale_width / self.source_width
        else:
            self.scale = 1.0
        self.work_w = max(1, int(self.source_width * self.scale))
        self.work_h = max(1, int(self.source_height * self.scale))
        self.started_at = time.time()
        return self.fps, self.work_w, self.work_h

    def read(self) -> Optional[np.ndarray]:
        """Next frame at working size, or None at end of file / unplugged."""
        if self.cap is None:
            return None
        ok, frame = self.cap.read()
        if not ok or frame is None:
            return None
        self.frames_read += 1
        if self.is_file:
            # Recorded video: use the video's own clock, so speeds and durations are
            # in game time no matter how fast this machine processes the file.
            self.last_timestamp = self.started_at + (self.frames_read - 1) / max(1, self.fps)
        else:
            self.last_timestamp = time.time()
        if self.scale != 1.0:
            frame = cv2.resize(frame, (self.work_w, self.work_h), interpolation=cv2.INTER_AREA)
        return frame

    def note_brightness(self, is_black: bool) -> None:
        self._black_run = self._black_run + 1 if is_black else 0

    @property
    def no_signal(self) -> bool:
        """True after black_seconds of black frames (HDCP on, console asleep, wrong input)."""
        return self._black_run >= self.black_seconds * max(1, self.fps)

    def mode_mismatch(self) -> Optional[str]:
        """Describe it when the card didn't give the resolution that was asked for."""
        w, h = self.requested.get("width"), self.requested.get("height")
        if self.is_file or not w or not h or (self.source_width, self.source_height) == (w, h):
            return None
        return (
            f"capture card delivers {self.source_width}x{self.source_height}, not the requested {w}x{h}. "
            "Check the console's video output setting, or set capture.width/height in device_config.json."
        )

    def info(self) -> Dict[str, Any]:
        return {
            "device": str(self.device),
            "source": f"{self.source_width}x{self.source_height}",
            "working": f"{self.work_w}x{self.work_h}",
            "fps": self.fps,
            "frames_read": self.frames_read,
        }

    def close(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def __enter__(self) -> "HdmiCapture":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()


# Backwards-compatible name used by older scripts.
HDMI_Capture = HdmiCapture
