# Dashboard: your match history in any browser

Leetify gives CS2 players a website with their match history and stats. GameTrainer's version
runs on **your host device** (the Raspberry Pi, laptop, or desktop the console plugs into), so
you can open it from a phone, a laptop, or the TV's browser on the same network. There are
no accounts and no cloud, nothing is uploaded, and it doesn't host game servers. It's a
read-only web page over your own `data/gameplay.db`.

```bash
gametrainer --serve
```

```
GameTrainer dashboard (read-only) serving data/gameplay.db
  This computer:   http://localhost:8765
  Your network:    http://192.168.1.40:8765   (phones, laptops, TV browsers)
```

Open the "Your network" address on any device on the same Wi-Fi or LAN.

## Track and serve at the same time

```bash
gametrainer smash --serve --build-replay        # track Smash and serve the dashboard
```

Or keep the dashboard running in one terminal and track in another. The page refreshes
itself, and a match being tracked shows a **LIVE** badge. Its stats and replay update every
few seconds.

## What's on it

| Tab | Shows |
|---|---|
| **Matches** | Every tracked match, newest first, filterable by game. Open one for the **replay** (drawn from data points in each player's measured color, with play, scrub, and 0.5–4× speed), the **scoreboard**, the final HUD readings (lap, position, damage %, score), and events |
| **Career** | Per game and player slot (p1, p2 ...): matches, time played, usual car/skin, average of every stat, and a trend line across matches |
| **Games** | Every game profile (bundled and your own) with its short name and tracking command |
| **Consoles** | Every supported console with its wiring, HDCP, and output settings |

On a match's scoreboard, **▲ / ▼** compares each stat with that player's average for the same
game, which tells you whether you played better or worse than usual. Speeds and distances are
in screen pixels, so compare them only within one game.

## Options

| Option | Default | Meaning |
|---|---|---|
| `--serve` | | Serve the dashboard. With a game, track and serve |
| `--host` | `0.0.0.0` | `0.0.0.0` = reachable from your network; `127.0.0.1` = this computer only |
| `--port` | `8765` | Port to listen on. Pick another if something already uses it |
| `--output` / `--db` | `./data` | Which data folder or database to show |

## Start it on boot (Raspberry Pi OS / Linux)

```bash
cd ~/GameTrainer                      # the folder whose data/ you want to serve
gametrainer --install-service         # writes ~/.config/systemd/user/gametrainer-dashboard.service
systemctl --user daemon-reload && systemctl --user enable --now gametrainer-dashboard.service
sudo loginctl enable-linger $USER     # keep it running when nobody is logged in
```

Stop it with `systemctl --user disable --now gametrainer-dashboard.service`. On Windows or
macOS, add `gametrainer --serve` to your login items instead.

## Cost on a Raspberry Pi

The server uses Python's standard library, so it adds no dependencies. It does nothing until
a page asks for data. A finished match's replay is built once and cached as
`data/replays/<session>.json`; a live match is rebuilt at most every 5 seconds. Responses
over 2 KB are gzipped to keep Wi-Fi traffic small. Tracking speed is unaffected in practice:
`python verify_tracker.py` still enforces 30 fps tracking on a Pi 4.

## Safety

- It's **read-only**: no page or API call changes your data or settings.
- Only sessions that exist in the database can be opened. Anything else, including path
  tricks like `../`, gets a 404.
- Anyone on your network can see your match history while it runs. To keep it private, use
  `--host 127.0.0.1`, or only run it on a network you trust. Don't forward the port to the
  internet.

## JSON API

Everything the page shows comes from these `GET` endpoints, so you can build your own tools on
them:

| Endpoint | Returns |
|---|---|
| `/api/health` | version, whether the database exists |
| `/api/overview` | match count, time tracked, live sessions, matches per game |
| `/api/sessions[?game=NAME]` | match history, newest first |
| `/api/sessions/<id>` | one match: players, stats, `vs_average` per stat, events, `final_hud` |
| `/api/sessions/<id>/replay` | the full data-point replay (the same format as `replay.json`) |
| `/api/career[?game=NAME]` | averages and per-match trend per game and player slot |
| `/api/games` | game profiles: name, console, kind, short names, players, HUD zones |
| `/api/consoles` | supported consoles: wiring chain, HDCP, output settings |

From Python: `middleware.server.store.Store("./data")` gives you the same data without the
web server.
