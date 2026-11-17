# GameTrainer — Command Reference

`gametrainer` (the desktop binary), `python track_game.py`, and `python .` are the same
program. What it does depends on the argument you pass:

| You pass | It does |
|---|---|
| nothing | lists the game profiles |
| a game profile (path, filename, or short name such as `smash`) | tracks live from the capture device |
| a replay file (any `.json` with a top-level `timeline`) | opens the replay viewer |
| `--build-replay` and no profile | builds a replay from an existing database |

## Examples

```bash
gametrainer                                   # list profiles
gametrainer --setup                           # guided first-time setup
gametrainer --check                           # is this host ready to track?
gametrainer --wiring ps5                      # how to connect a console (switch, ps5, ps4, xbox)
gametrainer --list-devices --save             # find the capture card and save its index
gametrainer --new-game "Rocket League" --kind racer --players 2
gametrainer rocket_league --calibrate         # click a player, press their number: color saved
gametrainer smash --pick 640,360 --set p1 --image shot.png   # same, without a screen

gametrainer smash --device 0                  # track Smash Bros. (passthrough: TV on the card)
gametrainer smash --monitor                   # the host shows the game full screen on its HDMI
gametrainer smash --build-replay --view       # track, then build and open the replay
gametrainer kart --seconds 300 --preview      # 5 minutes, with a live overlay window
gametrainer console_generic --device ./match.mp4   # track a recorded video file

gametrainer --list-sessions                   # sessions recorded in ./data/gameplay.db
gametrainer --build-replay --stats            # replay of the latest session + scoreboard
gametrainer ./data/replays/replay.json --stats   # scoreboard of a saved replay
gametrainer --build-replay --session 20261109-120844-e37b0e
gametrainer ./data/replays/replay.json        # view a replay

gametrainer smash --synthetic --build-replay  # try it with no console: generated test match
```

## Options

### Setup

| Option | Meaning |
|---|---|
| `--setup` | Guided setup: host check → console and wiring → capture card → game (or new game) → colors → 10-second test. Re-run any time |
| `--check` | System check: host device (model, USB 3, screen, Pi power), packages, configs, profiles, permissions, capture card, USB link, best capture mode |
| `--new-game NAME` | Create `config/games/<name>.json`. With `--kind fighter\|racer\|shooter\|any`, `--players N` (default 2), `--console` |
| `--wiring CONSOLE` | Wiring, HDCP, and output settings for `switch`, `ps5`, `ps4`, `xbox`, `xb1`, or `generic`, plus the splitter alternative |
| `--list-devices` | Probe video indexes 0–9: name, resolution, delivering frames, USB 2/3 |
| `--save` | With `--list-devices`: write the capture card's index to `./config/device_config.json` |
| `--calibrate` | Window with the live picture (or `--image`). **Space** freezes it, **click** a player, press their **number** to save the color into the profile; circles show what is detected now. `s` saves a frame, `q` quits. Without a display it saves `data/calibration.png` and explains `--pick` |
| `--pick X,Y` | The color at pixel X,Y of `--image` (or a frame from the capture device) |
| `--set PLAYER` | With `<game> --pick`: save that color into the player (`p1`, entity name, or number) |
| `--image PATH` | Screenshot for `--pick` / `--calibrate`, scaled to 1280 wide like the tracker |

### Tracking and replays

| Option | Default | Meaning |
|---|---|---|
| `--device N\|PATH` | `device.index` in `device_config.json` | Video device index, or a video file path |
| `--frames N` | unlimited | Stop after N processed frames |
| `--seconds S` | unlimited | Stop after S seconds |
| `--output DIR` | `./data` | Where `gameplay.db` is written |
| `--monitor` | off | Show the game full screen on the host's display while tracking (wiring B: host HDMI → TV). Esc/q stops |
| `--windowed` | off | With `--monitor`: a window instead of full screen |
| `--preview` | off | Live window showing tracked players and HUD values (press `q` to stop) |
| `--quiet` | off | Don't print a line per frame |
| `--synthetic` | off | Track a generated test match (`<output>/test/synthetic_game.mp4`, created on first use) |
| `--build-replay` | off | After tracking, build a replay of that session. With no profile, build from the database |
| `--view` | off | Open the viewer right after `--build-replay` |
| `--stats` | off | Print the per-player scoreboard (with `--build-replay`, or for a replay file) |
| `--db PATH` | `<output>/gameplay.db` | Database for `--build-replay` / `--list-sessions` |
| `--session ID` | latest session | Session to build a replay from |
| `--list-sessions` | | List recorded sessions with game, frame count, and duration |
| `--replay-output PATH` | `./data/replays/replay.json` | Where the replay JSON is written |
| `--version` | | Print the version |

Stop live tracking with **Ctrl+C**. Data captured so far is kept, and `--build-replay` still runs.

While tracking, GameTrainer warns you when the card delivers a different resolution than
requested, and when the picture has been black for 3 seconds (HDCP on a PS4/PS5, the
console asleep, or HDMI plugged into the wrong port).

## Sessions

Each tracking run is a **session** with its own id (date, time, and a short random suffix).
Every row it writes to `gameplay.db` is tagged with that id, so matches never mix, even if you
play several in a row. Databases from older versions have no session ids. Their frames are
grouped into 5-minute windows and listed as `legacy_<n>_<timestamp>`.

## Where config is read from

Config is read from `./config/` in the folder you run from first, then from the bundled copy.
To customise the binary, create `config/device_config.json` or `config/games/<game>.json` next
to where you run it. Files there override the bundled files with the same name.

## Checking an install without a capture card

```bash
python verify_tracker.py
```

This runs 50 end-to-end checks on a generated match:
- tracking accuracy against the true positions, and players never swapped
- car/skin colors
- separate sessions, replay contents, and stats
- older databases
- headless viewer rendering
- the CLI
- every middleware module
- the setup helpers (new game, saving colors, device index, wizard)
- the analyzer and profiler

It works in a temporary folder, and exit code 0 means everything passed. `./run_tests.sh`
runs the system check first, then this.
