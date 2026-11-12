# GameTrainer — Middleware

The middleware sits between the capture card and the replays. It turns the console's HDMI
picture into data points: who is where, what they look like, and what the HUD says.
It runs on the CPU only.

```
console ─HDMI─▶ capture card ─HDMI passthrough─▶ TV
                     │ USB
                     ▼
 HdmiCapture ─▶ FrameProcessor ─▶ GameTracker ─▶ gameplay.db ─▶ ReplayEngine ─▶ replay.json
 (frames)       (detections)      (sessions)                    (+ FeatureExtractor stats)
                                                                        │
                                                    GameSimulator / ReplayViewer
```

## Setup

`gametrainer --setup` walks through everything below interactively. Or step by step:

```bash
python3 install_middleware.py          # venv, install, system check, 50-check verification
gametrainer --wiring ps5               # how to connect your console (switch, ps5, ps4, xbox)
gametrainer --list-devices --save      # find the capture card and remember its index
gametrainer smash --calibrate          # click a player, press their number: color saved
gametrainer smash --build-replay --view
```

`gametrainer --check` re-runs the system check at any time. Each line is OK, WARN, FAIL, or INFO:

| Check | What it looks at |
|---|---|
| Host device | Model (e.g. Raspberry Pi 4), CPU, RAM, 64-bit OS |
| USB 3 ports / Screen output | The host has a USB 3 port for the card and a connected HDMI output |
| Pi power | Raspberry Pi: under-voltage or heat throttling since boot (`vcgencmd`) |
| Python, numpy, OpenCV, pygame, pandas | Installed and importable; pytesseract is optional |
| OpenCV camera backends | V4L2 (Linux), DirectShow/MSMF (Windows), AVFoundation (macOS) |
| Device config | `device_config.json` found and valid |
| Profile … | Every game profile loads and validates (colors, methods, ROI, templates) |
| Data folder | Writable, with free space |
| Permission to open cameras | Linux: user is in the `video` group |
| v4l2-ctl | Linux, optional: lists the card's modes |
| Display | Needed for the viewer, `--preview`, and `--calibrate` |
| Capture card / USB link / Capture mode | The card is found at the configured index, it's on USB 3, and the best mode it offers |

## Modules

### `middleware/capture/`

| Module | Purpose |
|---|---|
| `hdmi_capture.HdmiCapture` | Opens the card (V4L2 on Linux, DirectShow on Windows) or a video file. Requests the configured mode (1080p60 MJPG), downscales to the working size, and timestamps frames: wall clock when live, the video's own clock for files. Flags 3 s of black picture (`no_signal`) and a card that ignored the requested resolution (`mode_mismatch()`). |
| `usb_capture` | `list_devices()` and `find_capture_card()`: index, name, resolution, whether it delivers frames, and the USB link speed (Linux). |
| `game_tracker.GameTracker` | One tracking session: capture → frame processor → `gameplay.db`, batched writes, a session id on every row. `init_database()` upgrades older databases in place. |
| `synthetic` | Generated test match (green p1, red p2) for running without hardware. |
| `monitor_display.LiveMonitor` | Monitor mode: shows every full-resolution frame full screen on the host's display (`--monitor`), so the host can drive the TV. |

### `middleware/analysis/`

| Module | Purpose |
|---|---|
| `frame_processor.GameProfile` | Loads and **validates** a game profile; `apply_machine_limits()` applies `device_config.json` caps. |
| `frame_processor.FrameProcessor` | Detection on one frame, with no I/O: color, template, or motion detection, appearance (car/skin plus measured color), HUD OCR, and black-picture detection. Usable on screenshots. |
| `frame_processor.sample_color` | The color at a pixel, ready to paste into a profile (used by `--pick` and `--calibrate`). |
| `replay_engine.ReplayEngine` | Lists sessions and rebuilds one as a replay with its stats. |
| `feature_extractor` | Leetify-style stats per player: average and top speed, moving %, screen coverage, distance to the nearest opponent, close-quarters %. `format_stats()` prints the scoreboard. |

### `middleware/simulation/`

| Module | Purpose |
|---|---|
| `game_simulator.GameSimulator` | `state_at(t)`: player positions at any time, interpolated between samples; gaps longer than 0.5 s show as off screen. `play(fps)` streams states at a fixed rate. |
| `replay_viewer.ReplayViewer` | The pygame viewer: trails, timeline with events, stats panel. |

### `middleware/integration/`

| Module | Purpose |
|---|---|
| `system_integration` | Config lookup (`./config` first, then the bundled copy), `load_device_config()`, `save_device_index()`, and `run_session()`: track → replay → stats in one call. |
| `system_check` | `gametrainer --check` / `python check_system.py`. |
| `system_integration` (profiles) | `create_profile()` (`--new-game`), `set_entity_color()` (calibration). Edits to bundled profiles are saved as copies in `./config/games`. |
| `setup_wizard` | `gametrainer --setup`: host → console and wiring → capture card → game → colors → 10-second test that reports how often each player was seen. |

### `hardware_tools/`

| Module | Purpose |
|---|---|
| `host` | The host device: model (Raspberry Pi detection), USB 3 ports, connected screens, Pi under-voltage, requirements. |
| `adapters.hdmi_adapter` | Per-console wiring (passthrough or monitor mode), HDCP, and video-output settings (`gametrainer --wiring <console>`). |
| `adapters.usb_adapter` | USB 2 vs USB 3 advice for the card. |
| `drivers.capture_card_driver` | Card modes via `v4l2-ctl` and `best_mode()`: MJPG, 1080p, up to 60 fps. |
| `drivers.splitter_driver` | Setup for capture devices without passthrough (HDMI splitter + capture stick). |

The old class names (`HDMI_Capture`, `USB_Capture`, `Frame_Processor`) still work as aliases.

## Using it from Python

```python
from middleware.integration.system_integration import run_session

result = run_session("smash", device=0, seconds=300)        # or device="match.mp4"
print(result.session_id, result.replay_path, result.warnings)
for pid, s in result.stats["players"].items():
    print(pid, s["avg_speed_px_s"], s["close_quarters_pct"])
```

```python
import cv2
from middleware.analysis.frame_processor import FrameProcessor, GameProfile

proc = FrameProcessor(GameProfile("config/games/switch_smash_bros_ultimate.json"))
result = proc.process(cv2.imread("screenshot.png"))   # 1280-wide screenshot
for d in result["detections"]:
    print(d["player_id"], d["x"], d["y"], d["skin"])
```

## Verifying

```bash
./run_tests.sh             # system check (no device probe) + verify_tracker.py
```

`verify_tracker.py` runs 50 checks with no hardware: tracking accuracy, sessions, replays,
older databases, the viewer, the CLI, every middleware module above, the setup helpers, and
the analyzer and profiler.
