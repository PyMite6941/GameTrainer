"""
GameTrainer dashboard server: the host device serves your match history to any
browser on your network (phone, laptop, TV browser) - the Leetify-style web view.

    gametrainer --serve                     # http://<host-ip>:8765 on your network
    gametrainer --serve --host 127.0.0.1    # only this computer
    gametrainer --serve --port 9000

It is a read-only web page over the local gameplay.db: no accounts, no cloud,
nothing uploaded, and it never hosts game servers. Standard library only
(http.server), so it adds no dependencies and almost no CPU: run it alongside
tracking on a Raspberry Pi.

JSON API (all GET):
    /api/health                    version, database present
    /api/overview                  totals, live sessions, matches per game
    /api/sessions[?game=NAME]      match history, newest first
    /api/sessions/<id>             one match: players, stats, deltas vs career, events, final HUD
    /api/sessions/<id>/replay      the full data-point replay (timeline) for the browser viewer
    /api/career[?game=NAME]        career averages and trends per game and player slot
    /api/games                     bundled + user game profiles
    /api/consoles                  supported consoles and how to connect them
"""

from __future__ import annotations

import gzip
import json
import socket
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

from middleware.server.store import Store

STATIC_DIR = Path(__file__).resolve().parent / "static"
DEFAULT_PORT = 8765


def games_payload() -> Dict[str, Any]:
    from middleware.integration.system_integration import list_profiles

    games = []
    for path in list_profiles():
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        games.append({
            "profile": path.stem,
            "name": data.get("name", path.stem),
            "console": data.get("console", "generic"),
            "kind": data.get("kind"),
            "aliases": data.get("aliases", []),
            "description": data.get("description", ""),
            "players": [e.get("player_id") or e.get("name") for e in data.get("entities", [])],
            "hud": [z.get("name") for z in data.get("hud_zones", [])],
        })
    return {"games": games}


def consoles_payload() -> Dict[str, Any]:
    from hardware_tools.adapters.hdmi_adapter import console_setup, list_consoles

    return {"consoles": [{**c, "chain": console_setup(c["key"])["chain"]} for c in list_consoles()]}


def lan_addresses() -> list:
    """This machine's LAN IPv4 address(es), best guess first."""
    addrs = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.0.2.1", 9))  # TEST-NET address: no packet is sent for UDP connect
        addrs.append(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in addrs and not ip.startswith("127."):
                addrs.append(ip)
    except OSError:
        pass
    return addrs


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "GameTrainer"
    store: Store  # set on the subclass made by make_server
    version = "?"
    quiet = True

    # ------------------------------------------------------------ responses
    def _send(self, status: int, body: bytes, ctype: str, cache: str = "no-store") -> None:
        if len(body) > 2048 and "gzip" in self.headers.get("Accept-Encoding", ""):
            body = gzip.compress(body, compresslevel=5)
            self.send_response(status)
            self.send_header("Content-Encoding", "gzip")
        else:
            self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, payload: Any, status: int = 200) -> None:
        self._send(status, json.dumps(payload, default=str, separators=(",", ":")).encode(), "application/json")

    def _error(self, status: int, message: str) -> None:
        self._json({"error": message}, status)

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: D401 - http.server API
        if not self.quiet:
            super().log_message(fmt, *args)

    # -------------------------------------------------------------- routing
    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        url = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(url.query).items()}
        parts = [unquote(p) for p in url.path.split("/") if p]
        try:
            if not parts or parts == ["index.html"]:
                return self._send(200, (STATIC_DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
            if parts[0] != "api":
                return self._error(404, "not found")
            return self._api(parts[1:], query)
        except BrokenPipeError:
            pass
        except Exception as e:  # keep the server up; report the problem to the page
            self._error(500, f"{type(e).__name__}: {e}")

    def _api(self, parts: list, query: Dict[str, str]) -> None:
        store = self.store
        route: Tuple[str, ...] = tuple(parts)
        if route == ("health",):
            return self._json({"ok": True, "version": self.version, "database": store.has_db(),
                               "db_path": str(store.db_path)})
        if route == ("overview",):
            return self._json(store.overview())
        if route == ("sessions",):
            game = query.get("game")
            sessions = [s for s in store.sessions() if not game or s.get("game") == game]
            return self._json({"sessions": sessions})
        if len(route) in (2, 3) and route[0] == "sessions":
            sid = route[1]
            if len(route) == 2:
                summ = store.summary_with_deltas(sid)
                return self._json(summ) if summ else self._error(404, "no such session")
            if route[2] == "replay":
                replay = store.replay(sid)
                return self._json(replay) if replay else self._error(404, "no such session")
        if route == ("career",):
            return self._json(store.career(game=query.get("game")))
        if route == ("games",):
            return self._json(games_payload())
        if route == ("consoles",):
            return self._json(consoles_payload())
        return self._error(404, "unknown API path")


def make_server(data_dir: str = "./data", host: str = "0.0.0.0", port: int = DEFAULT_PORT,
                db_path: Optional[str] = None, version: str = "?", quiet: bool = True) -> ThreadingHTTPServer:
    store = Store(data_dir, db_path)
    handler = type("Handler", (DashboardHandler,), {"store": store, "version": version, "quiet": quiet})
    ThreadingHTTPServer.allow_reuse_address = True
    httpd = ThreadingHTTPServer((host, port), handler)
    httpd.daemon_threads = True
    return httpd


def serve(data_dir: str = "./data", host: str = "0.0.0.0", port: int = DEFAULT_PORT,
          db_path: Optional[str] = None, version: str = "?", quiet: bool = True) -> int:
    try:
        httpd = make_server(data_dir, host, port, db_path, version, quiet)
    except OSError as e:
        print(f"Can't start the dashboard on {host}:{port}: {e.strerror or e}")
        print("Another program may be using the port: try --port 9000")
        return 1
    real_port = httpd.server_address[1]
    print(f"GameTrainer dashboard (read-only) serving {Path(data_dir) / 'gameplay.db' if not db_path else db_path}")
    if host in ("0.0.0.0", ""):
        print(f"  This computer:   http://localhost:{real_port}")
        for ip in lan_addresses():
            print(f"  Your network:    http://{ip}:{real_port}   (phones, laptops, TV browsers)")
    else:
        print(f"  Open:            http://{host}:{real_port}")
    print("  Keep tracking in another terminal; the page refreshes itself. Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    finally:
        httpd.server_close()
    return 0


def serve_in_background(**kwargs: Any) -> Tuple[ThreadingHTTPServer, threading.Thread]:
    """Start the dashboard on a thread (used by tests and by tracking with --serve)."""
    httpd = make_server(**kwargs)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, thread
