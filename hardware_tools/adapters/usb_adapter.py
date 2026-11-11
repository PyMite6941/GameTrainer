"""
USB adapter: is the capture card on a link fast enough for the picture?

1080p60 in MJPG needs roughly 100-200 Mb/s; uncompressed YUY2 needs ~2 Gb/s, which
only USB 3 carries. A card on a USB 2 port (480 Mb/s) silently drops to a lower
mode, so GameTrainer checks the link and says which port to move it to.
"""

from __future__ import annotations

from typing import List

from middleware.capture.usb_capture import CaptureDevice, list_devices


def link_advice(dev: CaptureDevice) -> str:
    if dev.usb_speed_mbps is None:
        return f"index {dev.index}: USB speed unknown on this OS - use a USB 3 port (blue, or marked SS)."
    if dev.usb3:
        return f"index {dev.index}: on USB 3 ({dev.usb_speed_mbps} Mb/s) - good."
    return (
        f"index {dev.index}: on USB 2 ({dev.usb_speed_mbps} Mb/s). Move the card to a USB 3 port "
        "(blue, or marked SS) and avoid unpowered hubs; on USB 2 most cards can't deliver 1080p60."
    )


def check_links(max_index: int = 10) -> List[str]:
    return [link_advice(d) for d in list_devices(max_index) if d.delivering]


class UsbAdapter:
    def check(self) -> List[str]:
        return check_links()
