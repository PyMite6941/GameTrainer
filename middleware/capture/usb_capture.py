"""
USB capture-device discovery: which video index is the capture card?

The card's index changes with what else is plugged in (webcams, other cards),
so GameTrainer never hard-codes it. list_devices() probes indexes and reports
each device's name, resolution, whether it delivers frames, and - on Linux -
the USB link speed, because a card on a USB 2 port can't carry 1080p60.
"""

from __future__ import annotations

import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")

import cv2  # noqa: E402

from middleware.capture.hdmi_capture import open_capture  # noqa: E402

USB3_MBPS = 5000


@dataclass
class CaptureDevice:
    index: int
    name: str
    width: int
    height: int
    delivering: bool
    usb_speed_mbps: Optional[int] = None

    @property
    def usb3(self) -> Optional[bool]:
        return None if self.usb_speed_mbps is None else self.usb_speed_mbps >= USB3_MBPS

    @property
    def looks_like_capture_card(self) -> bool:
        return self.delivering and (self.width >= 1280 or "capture" in self.name.lower() or "hdmi" in self.name.lower())

    def describe(self) -> str:
        parts = [f"index {self.index}: {self.name or 'video device'}", f"{self.width}x{self.height}"]
        parts.append("delivering frames" if self.delivering else "opened, no frames")
        if self.usb_speed_mbps:
            parts.append(f"USB {'3' if self.usb3 else '2'} ({self.usb_speed_mbps} Mb/s)")
        return ", ".join(parts)

    def to_dict(self) -> dict:
        return asdict(self)


def _linux_name(index: int) -> str:
    try:
        return Path(f"/sys/class/video4linux/video{index}/name").read_text().strip()
    except OSError:
        return ""


def _linux_usb_speed(index: int) -> Optional[int]:
    """USB link speed of /dev/videoN from sysfs (480 = USB 2, 5000+ = USB 3)."""
    try:
        dev = Path(os.path.realpath(f"/sys/class/video4linux/video{index}/device"))
    except OSError:
        return None
    for d in (dev, *dev.parents):
        speed = d / "speed"
        if speed.is_file():
            try:
                return int(float(speed.read_text().strip()))
            except (OSError, ValueError):
                return None
        if d == Path("/sys"):
            break
    return None


def device_exists(index: int) -> bool:
    if sys.platform.startswith("linux"):
        return Path(f"/dev/video{index}").exists()
    return True


def probe(index: int) -> Optional[CaptureDevice]:
    """Open one index; None if nothing is there."""
    if not device_exists(index):
        return None
    cap = open_capture(index)
    try:
        if not cap.isOpened():
            return None
        ok, _ = cap.read()
        return CaptureDevice(
            index=index,
            name=_linux_name(index) if sys.platform.startswith("linux") else "",
            width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            delivering=bool(ok),
            usb_speed_mbps=_linux_usb_speed(index) if sys.platform.startswith("linux") else None,
        )
    finally:
        cap.release()


def list_devices(max_index: int = 10) -> List[CaptureDevice]:
    """Every video device at indexes 0..max_index-1 that opens."""
    return [d for d in (probe(i) for i in range(max_index)) if d is not None]


def find_capture_card(max_index: int = 10) -> Optional[CaptureDevice]:
    """The most likely capture card: delivering frames at the largest resolution."""
    devices = [d for d in list_devices(max_index) if d.delivering]
    if not devices:
        return None
    cards = [d for d in devices if d.looks_like_capture_card] or devices
    return max(cards, key=lambda d: d.width * d.height)


class UsbCapture:
    """Small facade kept for older scripts: is a capture device connected?"""

    def __init__(self, max_index: int = 10):
        self.max_index = max_index

    def devices(self) -> List[CaptureDevice]:
        return list_devices(self.max_index)

    def is_connected(self) -> bool:
        return any(d.delivering for d in self.devices())


USB_Capture = UsbCapture
