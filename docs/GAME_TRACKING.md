# GameTrainer — Game-Agnostic Console Tracking (CPU-only laptop)

## The core idea

Leetify improves Counter-Strike 2 players by parsing CS2 demo logs. Consoles (Switch,
PlayStation, Xbox) expose no demo files or game logs, so there is nothing to parse.
The generic console equivalent is **screen-capture computer vision**: the laptop watches
the exact same video the player sees on TV and extracts positions, actions, and HUD
stats from pixels. This repo already had the hardware layer (HDMI capture card +
passthrough); this adds the game-agnostic tracking layer on top.

## Hardware (any console)

Console dock → HDMI capture card HDMI In → card HDMI Out to TV (passthrough, zero added
lag) → card USB 3.0 to laptop. The card appears as a UVC webcam device, so
`cv2.VideoCapture(0)` opens it on the laptop.

Notes:
- **PS5:** disable HDCP (Settings > System > HDMI > turn off Enable HDCP) or the card
  gets a black signal.
- **Nintendo Switch:** must be docked (docked mode outputs HDMI). Handheld mode has no
  HDMI out; USB-C capture dongles exist but black out the console screen.
- Laptop needs only a USB 3.0 port — no GPU required.

## CPU-only tracking pipeline (median laptop device)

All detection runs on the CPU with OpenCV primitives. What keeps it light:

1. **Capture mode.** The card is asked for 1920x1080 at 60 fps in MJPG, so the full signal
   fits over USB. Without this, many cards fall back to 640x480.
2. **Working size.** Each frame is downscaled to `downscale_width` (1280) once.
3. **Frame stride.** Only every Nth frame is processed (`process_every_n_frames`, 2 by
   default). At 60 fps that is still 30 tracked frames per second.
4. **Detection scale.** Detectors run on a copy at `detect_scale` (0.5, a quarter of the
   pixels). Positions are scaled back, and appearance is sampled at full working size.
5. **Detection methods**, picked per entity in the game profile:
   - **color**: HSV hue segmentation around a target color; the largest blob's centroid.
   - **template**: grayscale `matchTemplate` against cropped character or item images.
   - **motion**: running-average background and frame differencing; the largest moving blob.
6. **Optional HUD OCR.** Tesseract reads the HUD zones every `ocr_every_n_frames` (15)
   processed frames and keeps the last value in between. It is only used when `pytesseract`
   and `tesseract-ocr` are installed. Everything else works without them.
7. **Batched writes.** Detections go to `data/gameplay.db` in one transaction per 30 frames,
   tagged with the session id.

Measured with `verify_tracker.py` on an idle Raspberry Pi 4 (4-core ARM), with two players at
1280x720: about 46 tracked frames per second with under 1 px average position error. A
typical x86 laptop is several times faster.

Frames from a live card are timestamped with the wall clock. Frames from a video file use
the video's own clock, so speeds and durations come out in game time however fast the file
is processed.

`config/device_config.json` sets limits per machine. Its `downscale_width`,
`process_every_n_frames`, and `detect_scale` can only make a profile lighter, never heavier.
On a slow machine, raise `process_every_n_frames` to 3 or lower `detect_scale` to 0.35.

## Adding a new game (no code changes)

Copy `config/games/console_generic.json` to `config/games/<game>.json` and edit it.

### `capture`

| Field | Default | Meaning |
|---|---|---|
| `resolution` | `[1920, 1080]` | The console's output resolution |
| `downscale_width` | 1280 | Working width; coordinates in the profile use this size |
| `process_every_n_frames` | 2 | Frame stride |
| `detect_scale` | 0.5 | Detector resolution relative to the working frame |
| `ocr_every_n_frames` | 15 | How often HUD zones are read |
| `roi` | whole frame | `[x1, y1, x2, y2]` play area; leave static HUD out of it |

### `entities`: one per thing to track

| Field | Meaning |
|---|---|
| `name` | Required; unique per profile |
| `player_id` | Stable id in the database and replays (`p1`, `p2`, ...). Defaults to `name` |
| `primary` | `true` for your own player |
| `method` | `color`, `template`, or `motion` |
| `color_bgr` | For `color`: the target color in **BGR** order (sample it from a screenshot) |
| `hue_tolerance` | For `color`: ± hue on OpenCV's 0–179 wheel. 8–15 keeps similar colors apart (default 12, max 45) |
| `min_sat`, `min_val` | For `color`: ignore greyish or dark pixels (defaults 60 / 50) |
| `min_area` | Smallest blob in working-frame pixels (color 100, motion 300) |
| `template`, `threshold` | For `template`: template name and match score 0–1 (default 0.6) |
| `appearance` | `"car"` (racers) or `"skin"` (default). Says which slot the measured color fills |
| `car`, `skin` | Optional fixed labels, such as `"car": "standard_kart"` or `"skin": "mario"` |
| `appearance_radius` | Pixels around the detection sampled for appearance (default 18) |

Each detection stores an appearance signature: the dominant color (BGR), color name,
saturation, and brightness of the player's colorful pixels. The car or skin label comes from
the profile if you set one. Otherwise it is the measured color name (`green`, `red`, `blue`,
and so on). The replay viewer draws every player in their measured color.

### `templates` and `hud_zones`

- `templates`: `{"name": ..., "file": "sprite.png"}`. The PNG sits next to the profile and is
  cropped at working-frame size. A missing file prints a warning when tracking starts.
- `hud_zones`: `{"name": "damage_p1", "entity": "damage_p1", "bbox": [x1, y1, x2, y2]}` in
  working-frame coordinates. Zones whose name starts with `damage` become damage events in
  the replay.

### Getting the colors right

Don't guess `color_bgr`. Measure it:

```bash
gametrainer smash --calibrate               # live picture; click each player
gametrainer --pick 512,300 --image shot.png # or one pixel of a 1280-wide screenshot
```

Each click prints `"color_bgr": [B, G, R]` and the hue. Paste it into the entity. With a
profile given, `--calibrate` circles what the profile detects right now, so you can check
the result straight away.

Then run it. Short names work:

```bash
gametrainer <game> --device 0 --preview     # --preview shows what is being tracked
```

All options are in [the command reference](CLI.md).

The analyzer and profiler read the same database:

```
python -c "from analyzer import OpponentAnalyzer; OpponentAnalyzer('./data/gameplay.db').save_profile()"
python -c "from player_profiler import create_player_profile; create_player_profile('player_1', './data/gameplay.db')"
```

## Output

- `data/gameplay.db`: sessions, per-frame positions and appearance per player, HUD readings, game states.
- `data/opponent_profile.json` — opponent tendencies (movement, action states).
- `./profiles/<player>_profile.json` — play-style profile (movement, decisions,
  tactics, physical, psychological traits) for the behavior-replay trainer.

## Limitations

- No in-game memory/state access: everything is inferred from pixels, so results are
  only as good as the profile tuning (colors, templates, zones).
- OCR is optional and can misread stylized game fonts; prefer color/template tracking
  where possible.
- Switch handheld mode is not directly capturable.
