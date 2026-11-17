# GameTrainer

GameTrainer tracks your console games and lets you review them like Leetify does for CS2:
replays and stats built from **data points, not video**. It works with Switch, PlayStation, and
Xbox, and runs on a **Raspberry Pi, laptop, or desktop** with no GPU.

Leetify coaches CS2 players by parsing demo files. Consoles don't produce demo files, so
GameTrainer watches the console's HDMI picture through a capture card. It records where each
player is and what they look like (car, skin, color) and reads the HUD. After the match you
can scrub through the replay and see your stats.

**New here? Start with the [Tutorial](TUTORIAL.md).**

## How it connects

```
                         ┌──── HDMI Out ──▶ TV   (A: passthrough, no lag)
Console ─HDMI─▶ Capture card
                         └──── USB 3 ──▶ Host device ──HDMI──▶ TV   (B: --monitor)
                                         Raspberry Pi 4/5, laptop or desktop
                                         track ▶ gameplay.db ▶ replay + stats ▶ viewer
```

The **host device** is whatever computer the console connects to. It needs a USB 3 port for
the capture card, plus an HDMI out if it drives the screen. See [Hardware setup](HARDWARE_SETUP.md).

## Quick start

```bash
python3 install_middleware.py && source .venv/bin/activate
gametrainer --setup                                  # guided: host, wiring, card, game, colors
gametrainer smash --build-replay --stats --view      # play, then review
```

No console handy? `gametrainer smash --synthetic --build-replay --stats --view` runs the
whole flow on a generated test match.

## Guides

- [**Tutorial**](TUTORIAL.md): try it in 5 minutes, then set up your console in 15
- [Hardware setup](HARDWARE_SETUP.md): the host device and its ports, wiring (passthrough or monitor mode), consoles
- [Installation](INSTALLATION.md): installer, binary, or by hand; troubleshooting
- [Software setup](SOFTWARE_SETUP.md): device config, game profiles, where data goes
- [Command reference](CLI.md): every command and option
- [Game tracking](GAME_TRACKING.md): how tracking works; adding and tuning a game
- [Replays and stats](REPLAY.md): the viewer, the stats, the replay format
- [Middleware](MIDDLEWARE.md): how the pieces fit together, and the Python API
- [Desktop binary](BINARY_INSTALL.md): build and share `dist/gametrainer`

## Supported out of the box

| Short name | Game |
|---|---|
| `smash` | Super Smash Bros. Ultimate (Switch) |
| `kart` | Mario Kart 8 Deluxe (Switch) |
| `console_generic` | Any game: tracks whatever moves |

Any other game: `gametrainer --new-game "Name" --kind fighter|racer|shooter|any`, then
`--calibrate`. No code or JSON editing is needed.

GameTrainer runs on desktop systems (Raspberry Pi OS, Linux, Windows, macOS), not phones.
