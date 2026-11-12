# Tutorial: your first tracked match

This walks you from nothing to reviewing a match's replay and stats. Part 1 needs no console
or capture card and takes about 5 minutes. Part 2 is the real setup, about 15 minutes.

**You'll need for Part 2:** a console, an HDMI capture card, and a host device with a
**USB 3 port**: a Raspberry Pi 4/5 (official power supply), a laptop, or a desktop. See
[Hardware setup](HARDWARE_SETUP.md) if you're not sure what to buy.

---

## Part 1 — Try it with no hardware (5 minutes)

### 1. Install

```bash
git clone https://github.com/PyMite6941/GameTrainer.git
cd GameTrainer
python3 install_middleware.py
source .venv/bin/activate          # Windows: .venv\Scripts\activate
```

The installer finishes with `50/50 checks passed` and a list of next steps. If it prints
commands with `sudo`, run them; they need admin rights, so it leaves them to you.

### 2. Track a generated test match

```bash
gametrainer smash --synthetic --build-replay --stats
```

GameTrainer generates a short match (a green player and a red player), tracks it like real
gameplay, rebuilds it from the data points, and prints a scoreboard:

```
player       on screen  avg speed  top speed  moving  coverage  opp dist  close
p1                100%     420px/s     561px/s    100%       27%     478px    23%
p2                100%     420px/s     569px/s    100%       27%     478px    23%
```

### 3. Watch the replay

```bash
gametrainer ./data/replays/replay.json
```

Press **Space** to play. Drag the timeline to scrub, and press **Up/Down** to change speed and
**T** to toggle movement trails. Everything you see is redrawn from tracked positions; no video
was saved.

That is the whole loop: **track → replay → stats**. Part 2 does the same with your console.

---

## Part 2 — Your console (15 minutes)

The easy way is the guided setup, which asks simple questions and does steps 1–5 below for you:

```bash
gametrainer --setup
```

The same steps by hand:

### 1. Check the host

```bash
gametrainer --check
```

Look for `[FAIL]` lines and fix them first. The most common ones:

| Line | Fix |
|---|---|
| `Permission to open cameras` | `sudo usermod -aG video $USER`, then log out and back in |
| `Pi power … under-voltage` | Use the official Raspberry Pi power supply |
| `USB 3 ports … only USB 2` | Use a host with USB 3, or a USB 2 capture stick at 1080p30 |

### 2. Wire it up

```bash
gametrainer --wiring switch        # or ps5, ps4, xbox
```

Follow the printed steps. In short: console HDMI → capture card **HDMI In**, card **USB** → a
**blue/SS** USB port on the host. Then for the screen, pick one:
- **Passthrough** (best): card **HDMI Out** → TV.
- **Monitor mode:** host HDMI → TV, and add `--monitor` when you play.

On a PS4 or PS5, turn **HDCP off** first.

### 3. Find the capture card

Turn the console on, then:

```bash
gametrainer --list-devices --save
```

```
Video devices (a capture card usually reports 1920x1080 or 1280x720):
  index 0: USB Video: USB Video, 1920x1080, delivering frames, USB 3 (5000 Mb/s)

Most likely capture card: index 0
Saved device.index = 0 to config/device_config.json
```

### 4. Pick or create your game

Included: Smash Bros. Ultimate (`smash`), Mario Kart 8 Deluxe (`kart`), and a generic
"anything that moves" profile (`console_generic`). For another game:

```bash
gametrainer --new-game "Rocket League" --kind racer --players 2 --console ps5
```

`--kind` is `fighter`, `racer`, `shooter`, or `any`. Use `any` if you're unsure: it tracks
whatever moves, with no colors needed.

### 5. Teach it the players' colors

Start a match on the console, then:

```bash
gametrainer rocket_league --calibrate
```

A window shows the live game:
1. Press **Space** to freeze the picture.
2. **Click** player 1's main color (kart body, costume, team color), then press **1**.
3. Click player 2, then press **2**, and so on.
4. White circles now follow each player. Press **Space** to unfreeze and check they keep
   following, then press **q**.

Each number key saves that color into the game's profile straight away.

No screen on the host? `--calibrate` saves a screenshot instead and tells you the
`--pick X,Y --set p1` command to use.

### 6. Play a match

```bash
gametrainer rocket_league --build-replay --stats --view
# monitor mode:  gametrainer rocket_league --monitor --build-replay --stats --view
```

Play normally. When the match ends, press **Ctrl+C** in the terminal, or **q** on the monitor
screen. GameTrainer builds the replay, prints the scoreboard, and opens the viewer.

---

## Reading your stats

| Stat | What it tells you |
|---|---|
| **on screen** | How reliably you were tracked. Below ~80% means recalibrate that player |
| **avg / top speed** | How fast you move around. Compare matches of the same game |
| **moving** | Share of time on the move rather than standing still |
| **coverage** | How much of the screen you used. Low means you stay in one area |
| **opp dist / close** | How close you play to opponents. High *close* means an aggressive, close-range style |

Every match is a separate session. To look back at older ones:

```bash
gametrainer --list-sessions
gametrainer --build-replay --session <id> --stats
```

## When something's off

| Symptom | Try |
|---|---|
| `Capture error` | `gametrainer --list-devices --save` |
| Black picture warning | PS4/PS5: HDCP off. Is the console on? Is HDMI in the card's **In** port? |
| A player shows "not detected" | `gametrainer <game> --calibrate` again on a clearer moment |
| Tracking jumps to the background | Click a more distinctive part of the player when calibrating |
| Slow on a Pi or an older laptop | Copy `config/setup_examples/slow_laptop.json` to `config/device_config.json` |
| Anything else | `gametrainer --check` |

Next: [Command reference](CLI.md) · [Game profiles in depth](GAME_TRACKING.md) ·
[Replays and stats](REPLAY.md)
