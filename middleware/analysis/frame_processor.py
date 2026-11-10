"""
Frame processing: everything GameTrainer reads from one captured frame.

Pure CPU OpenCV, no I/O. Given a game profile and a working-size BGR frame,
FrameProcessor returns where each tracked player is, what they look like
(car / skin / measured color), and the HUD values:

  * color segmentation   HSV hue range around a target color, largest blob
  * template matching    cv2.matchTemplate on grayscale crops
  * motion detection     running-average background + frame differencing
  * appearance           dominant color of the player's colorful pixels
  * HUD OCR (optional)   Tesseract, only if pytesseract + tesseract-ocr exist

GameTracker (middleware.capture.game_tracker) feeds it frames from the capture
card and stores the results; it can also be used on its own to tune a profile
against screenshots.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

try:
    import pytesseract  # type: ignore

    try:
        pytesseract.get_tesseract_version()
        TESSERACT_AVAILABLE = True
    except Exception:  # python package present but tesseract binary missing
        TESSERACT_AVAILABLE = False
except ImportError:
    TESSERACT_AVAILABLE = False


DEFAULT_HUE_TOLERANCE = 12
MAX_HUE_TOLERANCE = 45
BLACK_FRAME_LEVEL = 8  # mean brightness below this = no picture (e.g. HDCP)

# Coarse color names for appearance tags, keyed by upper hue bound (OpenCV hue 0-179).
_HUE_NAMES = [
    (8, "red"),
    (22, "orange"),
    (35, "yellow"),
    (85, "green"),
    (100, "cyan"),
    (130, "blue"),
    (160, "purple"),
    (172, "pink"),
    (180, "red"),
]

Detection = Tuple[float, float, float]  # x, y, confidence


def color_name(hue: Optional[float], sat: float, val: float) -> str:
    """Name a color from HSV so car/skin tags are readable (e.g. 'green')."""
    if val < 50:
        return "black"
    if sat < 40:
        return "white" if val > 190 else "gray"
    if hue is None:
        return "gray"
    for bound, name in _HUE_NAMES:
        if hue < bound:
            return name
    return "red"


def sample_color(frame: np.ndarray, x: int, y: int, radius: int = 6) -> Dict[str, Any]:
    """Average color around (x, y): what to paste into a profile's color_bgr."""
    h, w = frame.shape[:2]
    x1, y1 = max(0, x - radius), max(0, y - radius)
    x2, y2 = min(w, x + radius + 1), min(h, y + radius + 1)
    patch = frame[y1:y2, x1:x2].reshape(-1, 3)
    bgr = [int(round(v)) for v in patch.mean(axis=0)]
    hsv = cv2.cvtColor(np.uint8([[bgr]]), cv2.COLOR_BGR2HSV)[0][0]
    return {
        "color_bgr": bgr,
        "hue": int(hsv[0]),
        "saturation": int(hsv[1]),
        "brightness": int(hsv[2]),
        "color_name": color_name(int(hsv[0]), int(hsv[1]), int(hsv[2])),
    }


class GameProfile:
    """A game tracking profile loaded from config/games/<game>.json."""

    def __init__(self, profile_path: Union[str, Path]):
        self.path = Path(profile_path)
        if not self.path.exists():
            raise FileNotFoundError(f"Game profile not found: {self.path}")

        with open(self.path, "r") as f:
            self.raw: Dict[str, Any] = json.load(f)

        self.name: str = self.raw.get("name", self.path.stem)
        self.console: str = self.raw.get("console", "generic")
        self.description: str = self.raw.get("description", "")
        capture = self.raw.get("capture", {})
        res = capture.get("resolution", [1920, 1080])
        self.native_width: int = int(res[0])
        self.native_height: int = int(res[1])
        self.downscale_width: int = int(capture.get("downscale_width", 1280))
        self.process_every_n: int = max(1, int(capture.get("process_every_n_frames", 2)))
        self.ocr_every_n: int = max(1, int(capture.get("ocr_every_n_frames", 15)))
        # Detection runs on a smaller copy of the frame (0.5 = quarter of the pixels);
        # coordinates are scaled back, and appearance is sampled at full working size.
        self.detect_scale: float = min(1.0, max(0.2, float(capture.get("detect_scale", 0.5))))
        self.roi: Optional[List[int]] = capture.get("roi")  # [x1, y1, x2, y2] in working-frame space
        self.entities: List[Dict[str, Any]] = self.raw.get("entities", [])
        self.templates: List[Dict[str, Any]] = self.raw.get("templates", [])
        self.hud_zones: List[Dict[str, Any]] = self.raw.get("hud_zones", [])

        self.problems: List[str] = self.validate()
        if any(p.startswith("error:") for p in self.problems):
            raise ValueError(f"{self.path.name}: " + "; ".join(p[7:] for p in self.problems if p.startswith("error:")))

        # Preload grayscale templates (coords are in working-frame space)
        self._template_images: Dict[str, np.ndarray] = {}
        self.missing_templates: List[str] = []
        base_dir = self.path.parent
        for tmpl in self.templates:
            tpath = base_dir / tmpl.get("file", "")
            img = cv2.imread(str(tpath), cv2.IMREAD_GRAYSCALE) if tpath.is_file() else None
            if img is None:
                self.missing_templates.append(str(tpath))
                continue
            self._template_images[tmpl.get("name", tpath.stem)] = img

    def validate(self) -> List[str]:
        """Check the profile. Returns messages prefixed 'error:' or 'warning:'."""
        out: List[str] = []
        names = set()
        if not self.entities:
            out.append("warning: no entities - nothing will be tracked")
        for i, ent in enumerate(self.entities):
            name = ent.get("name")
            if not name:
                out.append(f"error: entity #{i + 1} needs a 'name'")
                continue
            if name in names:
                out.append(f"error: duplicate entity name '{name}'")
            names.add(name)
            method = ent.get("method", "color")
            if method not in ("color", "template", "motion"):
                out.append(f"error: entity '{name}' has unknown method '{method}'")
            if method == "color":
                c = ent.get("color_bgr") or ent.get("color")
                if not (isinstance(c, list) and len(c) == 3 and all(isinstance(v, (int, float)) and 0 <= v <= 255 for v in c)):
                    out.append(f"error: entity '{name}' needs color_bgr as [B, G, R] (0-255)")
                tol = ent.get("hue_tolerance", ent.get("tolerance"))
                if tol is not None and tol > MAX_HUE_TOLERANCE:
                    out.append(f"warning: entity '{name}' hue tolerance {tol} is capped at {MAX_HUE_TOLERANCE}")
            if method == "template" and not ent.get("template"):
                out.append(f"error: entity '{name}' uses method 'template' but names no template")
            if ent.get("appearance", "skin") not in ("car", "skin"):
                out.append(f"error: entity '{name}' appearance must be 'car' or 'skin'")
        if self.entities and not any(e.get("primary") for e in self.entities):
            out.append("warning: no entity is marked \"primary\": true - the first detection is used")
        if self.roi is not None and not (
            isinstance(self.roi, list) and len(self.roi) == 4 and self.roi[0] < self.roi[2] and self.roi[1] < self.roi[3]
        ):
            out.append("error: roi must be [x1, y1, x2, y2] with x1 < x2 and y1 < y2")
        for z in self.hud_zones:
            b = z.get("bbox")
            if not z.get("name") or not (isinstance(b, list) and len(b) == 4):
                out.append(f"error: hud zone {z.get('name', '?')} needs a name and bbox [x1, y1, x2, y2]")
        return out

    def apply_machine_limits(self, capture_cfg: Dict[str, Any]) -> None:
        """Let config/device_config.json cap CPU use on slower machines.

        The working width and detection scale become the smaller of the
        profile's and the machine's; the frame stride the larger.
        """
        dw = capture_cfg.get("downscale_width")
        if dw:
            self.downscale_width = min(self.downscale_width, int(dw))
        n = capture_cfg.get("process_every_n_frames")
        if n:
            self.process_every_n = max(self.process_every_n, int(n))
        ds = capture_cfg.get("detect_scale")
        if ds:
            self.detect_scale = min(self.detect_scale, max(0.2, float(ds)))

    def template_at(self, name: str, scale: float) -> Optional[np.ndarray]:
        """Template image resized to the detection scale (cached)."""
        key = f"{name}@{scale:.3f}"
        if key not in self._template_images:
            base = self._template_images.get(name)
            if base is None:
                return None
            w, h = max(1, int(base.shape[1] * scale)), max(1, int(base.shape[0] * scale))
            self._template_images[key] = cv2.resize(base, (w, h), interpolation=cv2.INTER_AREA)
        return self._template_images[key]

    def scale_factor(self, source_width: int) -> float:
        if self.downscale_width and source_width > self.downscale_width:
            return self.downscale_width / source_width
        return 1.0

    def working_size(self, source_width: int, source_height: int) -> Tuple[int, int]:
        scale = self.scale_factor(source_width)
        return max(1, int(source_width * scale)), max(1, int(source_height * scale))


class FrameProcessor:
    """Runs a game profile's detectors on working-size frames."""

    def __init__(self, profile: GameProfile):
        self.profile = profile
        self.bg_avg: Optional[np.ndarray] = None  # running background (motion detection)
        self._last_hud: Dict[str, Optional[str]] = {}

    @property
    def is_configured(self) -> bool:
        return bool(self.profile.entities) or bool(self.profile.hud_zones)

    # ----------------------------------------------------------------- detectors
    @staticmethod
    def hue_mask(hsv: np.ndarray, hue: int, tol: int, min_sat: int, min_val: int) -> np.ndarray:
        """inRange on the hue circle, wrapping around 0/179 when needed."""
        lo, hi = hue - tol, hue + tol
        mask = cv2.inRange(hsv, np.array([max(0, lo), min_sat, min_val]), np.array([min(179, hi), 255, 255]))
        if lo < 0:
            mask |= cv2.inRange(hsv, np.array([180 + lo, min_sat, min_val]), np.array([179, 255, 255]))
        if hi > 179:
            mask |= cv2.inRange(hsv, np.array([0, min_sat, min_val]), np.array([hi - 180, 255, 255]))
        return mask

    @staticmethod
    def _largest_blob(mask: np.ndarray, min_area: float) -> Optional[Tuple[Any, float]]:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best, best_area = None, 0.0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area >= min_area and area > best_area:
                best, best_area = cnt, area
        return (best, best_area) if best is not None else None

    @classmethod
    def track_by_color(
        cls,
        frame: np.ndarray,
        entity: Dict[str, Any],
        hsv: Optional[np.ndarray] = None,
        area_scale: float = 1.0,
    ) -> Optional[Detection]:
        """Largest blob matching the target color (HSV hue segmentation)."""
        color = entity.get("color_bgr") or entity.get("color", [0, 255, 0])
        tolerance = int(entity.get("hue_tolerance", entity.get("tolerance", DEFAULT_HUE_TOLERANCE)))
        tolerance = max(1, min(MAX_HUE_TOLERANCE, tolerance))
        min_area = max(1.0, int(entity.get("min_area", 100)) * area_scale)
        min_sat = int(entity.get("min_sat", 60))
        min_val = int(entity.get("min_val", 50))

        if hsv is None:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hue = int(cv2.cvtColor(np.uint8([[color]]), cv2.COLOR_BGR2HSV)[0][0][0])

        mask = cls.hue_mask(hsv, hue, tolerance, min_sat, min_val)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=1)
        blob = cls._largest_blob(mask, min_area)
        if blob is None:
            return None
        cnt, area = blob
        M = cv2.moments(cnt)
        if M["m00"] == 0:
            return None
        return M["m10"] / M["m00"], M["m01"] / M["m00"], min(1.0, area / (min_area * 10.0))

    def track_by_template(
        self, frame_gray: np.ndarray, entity: Dict[str, Any], scale: float = 1.0
    ) -> Optional[Detection]:
        tmpl_name = entity.get("template")
        tmpl = self.profile.template_at(tmpl_name, scale) if tmpl_name else None
        if tmpl is None:
            return None
        threshold = float(entity.get("threshold", 0.6))
        if tmpl.shape[0] > frame_gray.shape[0] or tmpl.shape[1] > frame_gray.shape[1]:
            return None
        res = cv2.matchTemplate(frame_gray, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val < threshold:
            return None
        h, w = tmpl.shape
        return max_loc[0] + w / 2, max_loc[1] + h / 2, float(max_val)

    def update_background(self, frame_gray: np.ndarray) -> Optional[np.ndarray]:
        """Advance the motion background once per frame; return the motion mask."""
        blur = cv2.GaussianBlur(frame_gray, (11, 11), 0)
        if self.bg_avg is None or self.bg_avg.shape != blur.shape:
            self.bg_avg = blur.astype("float")
            return None
        delta = cv2.absdiff(blur, cv2.convertScaleAbs(self.bg_avg))
        cv2.accumulateWeighted(blur, self.bg_avg, 0.5)
        thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
        return cv2.dilate(thresh, np.ones((5, 5), np.uint8), iterations=2)

    @classmethod
    def track_by_motion(
        cls, motion_mask: Optional[np.ndarray], entity: Dict[str, Any], area_scale: float = 1.0
    ) -> Optional[Detection]:
        """Largest moving region against the running-average background."""
        if motion_mask is None:
            return None
        min_area = max(1.0, int(entity.get("min_area", 300)) * area_scale)
        blob = cls._largest_blob(motion_mask, min_area)
        if blob is None:
            return None
        cnt, area = blob
        x, y, w, h = cv2.boundingRect(cnt)
        return x + w / 2, y + h / 2, min(1.0, area / (min_area * 10.0))

    # --------------------------------------------------------------- appearance
    @staticmethod
    def appearance_signature(
        work: np.ndarray, cx: int, cy: int, entity: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Optional[str], Optional[str]]:
        """Sample what a tracked player looks like around its detection.

        Returns (signature, car, skin). The signature holds the measured dominant
        color (from saturated pixels, so the background doesn't swamp it). car and
        skin come from the profile when it names them ("car": "standard_kart",
        "skin": "mario"); otherwise the measured color name fills the slot the
        entity's "appearance" field picks ("car" for racers, "skin" by default).
        """
        h, w = work.shape[:2]
        pad = int(entity.get("appearance_radius", 18))
        x1, y1 = max(0, cx - pad), max(0, cy - pad)
        x2, y2 = min(w, cx + pad), min(h, cy + pad)
        crop = work[y1:y2, x1:x2]
        sig: Dict[str, Any] = {"method": entity.get("method", "color")}
        measured = None
        if crop.size:
            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV).reshape(-1, 3)
            bgr = crop.reshape(-1, 3)
            colorful = (hsv[:, 1] >= 60) & (hsv[:, 2] >= 50)
            enough = colorful.sum() >= 10
            sample_hsv = hsv[colorful] if enough else hsv
            sample_bgr = bgr[colorful] if enough else bgr
            hist = np.bincount((sample_hsv[:, 0] // 10).astype(int), minlength=18)
            dominant_hue = int(np.argmax(hist)) * 10 + 5
            sat_mean = float(sample_hsv[:, 1].mean())
            val_mean = float(sample_hsv[:, 2].mean())
            measured = color_name(dominant_hue, sat_mean, val_mean)
            sig.update(
                {
                    "dominant_hue": dominant_hue,
                    "dominant_color_bgr": [round(float(v), 1) for v in sample_bgr.mean(axis=0)],
                    "color_name": measured,
                    "saturation": round(sat_mean, 1),
                    "brightness": round(val_mean, 1),
                    "colorful_fraction": round(float(colorful.mean()), 3),
                }
            )
        slot = entity.get("appearance", "skin")
        car = entity.get("car") or entity.get("appearance_label")
        skin = entity.get("skin")
        if slot == "car" and not car:
            car = measured
        elif slot != "car" and not skin:
            skin = measured
        return sig, car, skin

    # ---------------------------------------------------------------------- OCR
    @staticmethod
    def read_ocr(frame: np.ndarray, zone: Dict[str, Any]) -> Optional[str]:
        if not TESSERACT_AVAILABLE:
            return None
        x1, y1, x2, y2 = zone["bbox"]
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            return None
        gray = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        try:
            text = pytesseract.image_to_string(th, config="--psm 7").strip()
        except Exception:
            return None
        return text or None

    # -------------------------------------------------------------------- frame
    def roi_box(self, frame: np.ndarray) -> Tuple[int, int, int, int]:
        fh, fw = frame.shape[:2]
        roi = self.profile.roi
        if roi and len(roi) == 4:
            x1, y1 = max(0, int(roi[0])), max(0, int(roi[1]))
            x2, y2 = min(fw, int(roi[2])), min(fh, int(roi[3]))
            if x2 > x1 and y2 > y1:
                return x1, y1, x2, y2
        return 0, 0, fw, fh

    def process(self, frame: np.ndarray, frame_number: int = 0) -> Dict[str, Any]:
        """Detect every profile entity (and HUD zone) in one working-size frame.

        Returns {"detections", "primary", "hud", "roi", "black"}. Detection
        coordinates are in working-frame pixels.
        """
        x1, y1, x2, y2 = self.roi_box(frame)
        work = frame[y1:y2, x1:x2]

        s = self.profile.detect_scale
        small = (
            cv2.resize(work, (max(1, int(work.shape[1] * s)), max(1, int(work.shape[0] * s))),
                       interpolation=cv2.INTER_AREA)
            if s < 1.0 else work
        )
        black = float(small.mean()) < BLACK_FRAME_LEVEL
        area_scale = s * s
        methods = {e.get("method", "color") for e in self.profile.entities}
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY) if methods & {"template", "motion"} else None
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV) if "color" in methods else None
        motion_mask = self.update_background(gray) if "motion" in methods else None

        detections: List[Dict[str, Any]] = []
        primary: Optional[Dict[str, Any]] = None
        for entity in self.profile.entities:
            method = entity.get("method", "color")
            det: Optional[Detection] = None
            if method == "color":
                det = self.track_by_color(small, entity, hsv, area_scale)
            elif method == "template":
                det = self.track_by_template(gray, entity, s)
            elif method == "motion":
                det = self.track_by_motion(motion_mask, entity, area_scale)
            if det is None:
                continue
            cx, cy = int(round(det[0] / s)), int(round(det[1] / s))
            sig, car, skin = self.appearance_signature(work, cx, cy, entity)
            record = {
                "entity": entity["name"],
                "player_id": entity.get("player_id", entity["name"]),
                "x": cx + x1,
                "y": cy + y1,
                "confidence": round(det[2], 3),
                "method": method,
                "appearance": sig,
                "car": car,
                "skin": skin,
            }
            detections.append(record)
            if entity.get("primary", False) or primary is None:
                primary = record

        # HUD OCR: Tesseract is slow on CPU, so read every Nth processed frame and
        # carry the last value forward in between.
        hud: List[Dict[str, Any]] = []
        read_hud = TESSERACT_AVAILABLE and frame_number % self.profile.ocr_every_n == 0
        for zone in self.profile.hud_zones:
            if read_hud:
                value = self.read_ocr(frame, zone)
                fresh = value != self._last_hud.get(zone["name"])
                self._last_hud[zone["name"]] = value
                hud.append({"zone": zone["name"], "value": value, "fresh": fresh})
            elif zone["name"] in self._last_hud:
                hud.append({"zone": zone["name"], "value": self._last_hud[zone["name"]], "fresh": False})

        return {
            "detections": detections,
            "primary": primary or {"entity": "none", "x": None, "y": None, "method": None},
            "hud": hud,
            "roi": (x1, y1, x2, y2),
            "black": black,
        }


# Backwards-compatible name used by older scripts (check_system.py).
Frame_Processor = FrameProcessor
