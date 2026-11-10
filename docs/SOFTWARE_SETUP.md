# Software Setup

GameTrainer reads two kinds of configuration: one device config per machine, and one profile
per game. Both are looked up in `./config/` (the folder you run from) first, then in the
bundled copy. To customise the binary, put your own files in `./config/`.

## Device config: `config/device_config.json`

```json
{
  "device":  { "index": 0 },
  "capture": { "width": 1920, "height": 1080, "fps": 60, "fourcc": "MJPG",
               "downscale_width": 1280, "process_every_n_frames": 2, "detect_scale": 0.5 }
}
```

- `device.index`: the video device the capture card appears as. `gametrainer --list-devices --save`
  finds and saves it. Change it per machine, or override it with `--device N`.
- `width`, `height`, `fps`, `fourcc`: the mode requested from the capture card. MJPG lets
  1080p60 fit over USB; set `fourcc` to `""` if a card misbehaves with it.
- `downscale_width`, `process_every_n_frames`, `detect_scale`: limits for this machine.
  They can make any game profile lighter but never heavier. On a slow machine, try
  `process_every_n_frames: 3` or `detect_scale: 0.35`.
- GameTrainer opens no network ports. Capture is over USB.
- Missing keys fall back to the defaults shown above. Starting points for common setups are in
  `config/setup_examples/`.

## Game profiles: `config/games/*.json`

Each profile tells the tracker what to look for in one game: the play area, the players
(tracked by color, template, or motion), whether each player's look is a `car` or a `skin`,
and the HUD zones to read. Start by copying `console_generic.json`.
[Game tracking](GAME_TRACKING.md) lists every field. `gametrainer --check` validates every
profile, and tracking refuses a profile with errors such as a malformed `color_bgr` or an
unknown method.

To get a player's color, run `gametrainer <game> --calibrate` and click them in the live
picture. The terminal prints `"color_bgr": [...]` to paste into the entity.

Run a profile by path, filename, or short name: `gametrainer smash`, `gametrainer kart`,
`gametrainer console_generic`.

## Where data goes

| Path | Contents |
|---|---|
| `data/gameplay.db` | Sessions, plus per-frame positions, appearance, and HUD readings (no video) |
| `data/replays/replay.json` | The latest replay you built |
| `data/test/synthetic_game.mp4` | The generated test match (`--synthetic`) |
| `data/opponent_profile.json`, `profiles/` | Analyzer and play-style profiles |

`config/middleware_config.json` belongs to the older demo system (`main.py`). The tracker
doesn't read it; `device_config.json` is the tracker's config.
