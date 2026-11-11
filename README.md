# GameTrainer

CPU-only console gameplay tracker and data-point replay trainer — the Leetify model for any
Switch / PlayStation / Xbox game, running on a laptop (desktop only, not mobile).

## The model (like Leetify)

Leetify improves CS2 players by parsing demo logs. Consoles expose no demo files, so GameTrainer
watches the same video the player sees on TV and extracts positions, actions, and HUD stats from
pixels — then analyzes and replays from **data points, not video**.

## Hardware (one cable chain, any console)

Console dock HDMI Out → capture card HDMI In → card HDMI Out to TV (passthrough, zero lag, the TV
is your monitor during play) → card USB 3.0 to laptop. The card appears as a UVC video device.

- PS5: disable HDCP (Settings > System > HDMI > Enable HDCP = off).
- Nintendo Switch: must be docked (handheld has no HDMI out).

## What it tracks

Per frame, per player: position, appearance (car or skin, plus the measured color), detection
method (color / template / motion), and confidence. Optional HUD OCR adds damage %, lap, and
rank. Each run is a separate session in `data/gameplay.db`, and no video is stored.

## Quick start

```bash
python3 install_middleware.py                    # venv, install, system check, verification
source .venv/bin/activate
gametrainer --wiring switch                      # how to connect your console (ps5, ps4, xbox...)
gametrainer --list-devices --save                # find the capture card and remember it
gametrainer smash --calibrate                    # click players to get their colors
gametrainer smash --build-replay --stats --view  # play, then review
```

During the game the TV, fed by HDMI passthrough, is your monitor. When you press Ctrl+C the
match is rebuilt from data points, a per-player scoreboard prints (speed, movement, screen
coverage, time close to opponents), and the replay viewer opens with a scrubber, movement
trails, and event markers.

No console? `gametrainer smash --synthetic --build-replay --stats --view` runs the same flow
on a generated test match. `gametrainer --check` diagnoses setup problems.

## After the game: data-point replay (not video)

```bash
python track_game.py --list-sessions                 # every match you've tracked
python track_game.py --build-replay                  # rebuild the latest one
python track_game.py ./data/replays/replay.json      # scrub through it
```

## Reassignable device / ports

The capture device index and capture mode live in `config/device_config.json`. Change them
per machine, or pass `--device N`. `--list-devices` shows which index is the card.
GameTrainer opens no network ports: capture is local over USB.

## Add a game (no code changes)

Drop a JSON profile into `config/games/` with the play area, player colors or templates,
car/skin labels, and HUD zones. Start from `config/games/console_generic.json`. Every field is
listed in [`docs/GAME_TRACKING.md`](docs/GAME_TRACKING.md).

## Install as a desktop binary

```bash
./build_binary.sh                  # builds dist/gametrainer (one-file executable)
./dist/gametrainer --list-devices
./dist/gametrainer smash --device 0 --build-replay --view
```

Or install it as a command: `pip install .`, then run `gametrainer`. Desktop only, not mobile.

## Verify

```bash
./run_tests.sh                     # system check + 42 end-to-end checks, no capture card needed
```

## Docs

Full docs (GitHub Pages, served from `docs/`): start at [`docs/index.md`](docs/index.md).

- [`docs/MIDDLEWARE.md`](docs/MIDDLEWARE.md) — how capture, detection, sessions, and replays fit together
- [`docs/HARDWARE_SETUP.md`](docs/HARDWARE_SETUP.md) — cables, capture card, console notes
- [`docs/INSTALLATION.md`](docs/INSTALLATION.md) — binary or from-source install
- [`docs/SOFTWARE_SETUP.md`](docs/SOFTWARE_SETUP.md) — device config & game profiles
- [`docs/CLI.md`](docs/CLI.md) — every command and option
- `docs/GAME_TRACKING.md` — capture hardware + CPU tracking pipeline
- `docs/REPLAY.md` — data-point replay engine & viewer
- `docs/BINARY_INSTALL.md` — desktop binary build & install
