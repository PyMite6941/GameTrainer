# GameTrainer

Track your Switch, PlayStation, or Xbox games and review them like Leetify does for CS2:
replays and stats built from **data points, not video**. It runs on a **Raspberry Pi 4/5,
laptop, or desktop** (the "host device") with no GPU. Desktop systems only, not phones.

**New here? Follow the [Tutorial](docs/TUTORIAL.md)**: 5 minutes with no hardware, then 15 to
set up your console.

## The model (like Leetify)

Leetify improves CS2 players by parsing demo files. Consoles don't produce demo files, so
GameTrainer watches the console's HDMI picture through a capture card, extracts positions,
appearance, and HUD stats from the pixels, and replays and analyses the match from those
**data points, not video**.

## Hardware

- **Host device:** a Raspberry Pi 4/5 (official power supply), laptop, or desktop with a
  **USB 3 port**, and an HDMI out if it drives the screen.
- **Capture card:** HDMI In + USB. HDMI Out (passthrough) is recommended.
- **Wiring:** console → capture card HDMI In; card USB → host USB 3. For the screen, either
  card HDMI Out → TV (passthrough, no lag), or host HDMI → TV with `--monitor`.
- **Console settings:** PS4/PS5 need HDCP off. The Switch must be docked.

`gametrainer --check` tells you whether a host is ready. Details:
[docs/HARDWARE_SETUP.md](docs/HARDWARE_SETUP.md).

## What it tracks

Per frame, per player: position, appearance (car or skin, plus the measured color), detection
method (color / template / motion), and confidence. Optional HUD OCR adds damage %, lap, and
rank. Each run is a separate session in `data/gameplay.db`, and no video is stored.

## Quick start

```bash
python3 install_middleware.py && source .venv/bin/activate   # install + 50 self-checks
gametrainer --setup                                          # guided setup, step by step
gametrainer smash --build-replay --stats --view              # play, then review
```

`--setup` walks you through checking the host, wiring the console, finding the capture card,
choosing or creating your game, and clicking each player to teach it their colors. Prefer
separate commands? `--check`, `--wiring ps5`, `--list-devices --save`,
`--new-game "Name" --kind racer`, `<game> --calibrate`.

When the match ends (Ctrl+C, or q on the screen in monitor mode), the match is rebuilt from
data points, a per-player scoreboard prints (speed, movement, screen coverage, time close to
opponents), and the replay viewer opens.

No console? `gametrainer smash --synthetic --build-replay --stats --view` runs the same flow
on a generated test match.

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

```bash
gametrainer --new-game "Rocket League" --kind racer --players 2
gametrainer rocket_league --calibrate     # click a player, press their number
```

Profiles are JSON files in `config/games/`. Every field is listed in
[`docs/GAME_TRACKING.md`](docs/GAME_TRACKING.md).

## Install as a desktop binary

```bash
./build_binary.sh                  # builds dist/gametrainer (one-file executable)
./dist/gametrainer --list-devices
./dist/gametrainer smash --device 0 --build-replay --view
```

Or install it as a command: `pip install .`, then run `gametrainer`. Desktop only, not mobile.

## Verify

```bash
./run_tests.sh                     # system check + 50 end-to-end checks, no capture card needed
```

## Docs

Full docs (GitHub Pages, served from `docs/`): start at [`docs/index.md`](docs/index.md).

- [`docs/TUTORIAL.md`](docs/TUTORIAL.md) — your first tracked match, step by step
- [`docs/MIDDLEWARE.md`](docs/MIDDLEWARE.md) — how capture, detection, sessions, and replays fit together
- [`docs/HARDWARE_SETUP.md`](docs/HARDWARE_SETUP.md) — cables, capture card, console notes
- [`docs/INSTALLATION.md`](docs/INSTALLATION.md) — binary or from-source install
- [`docs/SOFTWARE_SETUP.md`](docs/SOFTWARE_SETUP.md) — device config & game profiles
- [`docs/CLI.md`](docs/CLI.md) — every command and option
- `docs/GAME_TRACKING.md` — capture hardware + CPU tracking pipeline
- `docs/REPLAY.md` — data-point replay engine & viewer
- `docs/BINARY_INSTALL.md` — desktop binary build & install
