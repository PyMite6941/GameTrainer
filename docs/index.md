# GameTrainer

GameTrainer tracks gameplay on any console on a laptop with no GPU, and builds replays from
**data points, not video**. It is the Leetify model for Switch, PlayStation, and Xbox games.

Leetify coaches CS2 players by parsing demo files. Consoles don't produce demo files, so
GameTrainer watches the same HDMI signal you see on the TV. It pulls positions, appearance
(car, skin, body color), and HUD stats out of each frame and saves them to a small database.
After the match you can rebuild it, scrub through it, and study it from that data.

## How it works

```
Console ──HDMI──▶ Capture card ──HDMI passthrough──▶ TV (your monitor while you play)
                       │
                     USB 3.0
                       ▼
                    Laptop: track ─▶ gameplay.db ─▶ replay.json ─▶ replay viewer
```

## Quick start

```bash
python3 install_middleware.py              # install, check, and verify (or ./build_binary.sh)
gametrainer --wiring switch                # how to connect your console
gametrainer --list-devices --save          # find the capture card
gametrainer smash --calibrate              # click players to tune their colors
gametrainer smash --build-replay --view    # play, then watch the replay and stats
```

No console handy? `gametrainer smash --synthetic --build-replay --stats --view` runs the
whole flow on a generated test match.

## Guides

- [Hardware setup](HARDWARE_SETUP.md): cables, capture cards, console notes
- [Installation](INSTALLATION.md): from source or as a desktop binary
- [Software setup](SOFTWARE_SETUP.md): device config and game profiles
- [Middleware](MIDDLEWARE.md): how capture, detection, sessions, and replays fit together, and the Python API
- [Command reference](CLI.md): every command and option
- [Game tracking](GAME_TRACKING.md): the CPU-only tracking pipeline, and adding a new game
- [Data-point replay](REPLAY.md): the replay engine, viewer controls, and replay format
- [Desktop binary](BINARY_INSTALL.md): build and ship `dist/gametrainer`

## Supported out of the box

| Profile | Game |
|---|---|
| `console_generic.json` | Starting template for any game |
| `switch_smash_bros_ultimate.json` | Super Smash Bros. Ultimate (Switch) |
| `switch_mario_kart_8_deluxe.json` | Mario Kart 8 Deluxe (Switch) |

To add a game, drop a JSON profile into `config/games/`. No code changes are needed.

GameTrainer is desktop only (Linux, Raspberry Pi, and other desktops). It is not a mobile app.
