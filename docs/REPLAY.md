# GameTrainer — Data-Point Replay (Leetify Model)

The replay system rebuilds a match entirely from the data points in `data/gameplay.db`.
No source video is needed. This is the console version of Leetify parsing CS2 demo files:
there are no demos, so GameTrainer uses the positions and appearance the tracker recorded.

## Pipeline

```
track (TV = monitor)  →  gameplay.db (one session per run)  →  build replay  →  replay.json  →  viewer
```

## Build a replay

```bash
gametrainer smash --build-replay --view   # track a match, then build and open its replay
gametrainer --build-replay                # later: replay of the latest session
gametrainer --list-sessions               # pick an older one...
gametrainer --build-replay --session 20261109-120844-e37b0e --replay-output ./data/replays/final.json
```

The output defaults to `./data/replays/replay.json`.

## View a replay (no video)

```bash
gametrainer ./data/replays/replay.json
```

| Control | Action |
|---|---|
| Space | Play / pause (plays at the match's real speed) |
| Up / Down | Double / halve playback speed (0.125×–8×) |
| Left / Right | Step one frame |
| Shift + Left / Right | Jump 5 seconds |
| Home / End | Jump to start / end |
| Click or drag the timeline | Scrub |
| T | Toggle movement trails |
| Esc / Q | Close |

The viewer draws each player in the color measured from the capture: their car, skin, or
body color. A fading trail shows their last 2 seconds of movement, and the arena keeps the
capture's aspect ratio. The side panel shows each player's car, skin, distance travelled,
on-screen time, and left/right split. Events (damage taken, action changes) show as red
ticks on the timeline. HUD values and game state appear under the arena.

## Stats (the Leetify part)

Every replay includes per-player stats computed from the data points:

```bash
gametrainer --build-replay --stats
gametrainer ./data/replays/replay.json --stats
```

```
player       on screen  avg speed  top speed  moving  coverage  opp dist  close
p1                100%     420px/s     561px/s    100%       27%     478px    23%
p2                100%     420px/s     569px/s    100%       27%     478px    23%
```

| Stat | Meaning |
|---|---|
| on screen | Share of frames the player was detected in |
| avg / top speed | Mean and 95th-percentile speed in working-frame px/s; the 95th percentile ignores one-frame tracking jumps |
| moving | Share of time faster than 30 px/s |
| coverage | Share of an 8×6 grid over the screen the player visited |
| opp dist / close | Average distance to the nearest other player, and how often it is under 15% of the screen diagonal (an engagement proxy) |

Speeds are in screen pixels, so compare players within a game rather than across games.
The viewer's side panel shows the same numbers.

## What's in replay.json (format_version 2)

| Key | Contents |
|---|---|
| `session_id`, `game`, `console` | Which match this is |
| `frame_size` | Working frame `[width, height]`, used to lay out the arena |
| `duration_seconds`, `total_frames`, `start_timestamp` | Timing |
| `players` | Per player: `car`, `skin`, `color_bgr`, `distance_traveled_px`, `frames_seen`, `seen_fraction`, `first_seen_t`, `last_seen_t`, `zone_time`, `appearance_samples` |
| `timeline` | Per frame: `t`, `frame`, `entities` (x/y, method, confidence, car, skin, appearance), `hud` (last known value of every zone), `game_state` |
| `events` | `damage_taken` (from HUD damage zones or game-state health) and `action` changes |
| `damage_events` | Every change in a HUD damage zone's value |
| `stats` | `players` (the stats above) and `match` (duration, frames, events, most active player) |
| `metadata` | Source database, generation time |

## Replay from data, not video

Because the replay is built from tracked coordinates and appearance, you can scrub a whole
match, compare players' paths, and compute stats without keeping any video. A replay of the
120-frame verification match is about 160 KB, smaller than the video it came from. For long
matches the difference grows, because the database stores a few numbers per player per frame.

## Using it from Python

```python
from middleware.analysis.replay_engine import ReplayEngine

engine = ReplayEngine("./data/gameplay.db")
for s in engine.load_sessions():
    print(s["session_id"], s["game"], s["frame_count"])
replay = engine.build_replay()                 # latest session
print(engine.replay_summary(replay))
engine.export_replay(replay, "./data/replays/replay.json")
print(replay["stats"]["players"]["p1"]["avg_speed_px_s"])

# Smooth playback at any rate: positions interpolated between samples
from middleware.simulation.game_simulator import GameSimulator
sim = GameSimulator(replay)
print(sim.state_at(12.5)["players"])
```
