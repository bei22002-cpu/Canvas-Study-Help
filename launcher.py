#!/usr/bin/env python3
"""
Canvas Study Help — Launcher
=============================
Starts the Canvas proxy server and serves the web UI, then opens the browser.

Usage (development):
    python3 launcher.py [--no-browser] [--enable-autostart] [--disable-autostart]

When packaged with PyInstaller, just double-click the app.

Environment variables:
    CANVAS_PROXY_PORT   Proxy port            (default: 3001)
    CANVAS_PROXY_HOST   Proxy host            (default: localhost)
    CANVAS_UI_PORT      UI static-server port (default: 4173)
    CANVAS_OPEN_BROWSER Set to "0" to suppress auto-open (default: 1)
"""

import argparse
import json
import logging
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("launcher")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROXY_PORT = int(os.environ.get("CANVAS_PROXY_PORT", "3001"))
PROXY_HOST = os.environ.get("CANVAS_PROXY_HOST", "localhost")
UI_PORT_DEFAULT = int(os.environ.get("CANVAS_UI_PORT", "4173"))
OPEN_BROWSER = os.environ.get("CANVAS_OPEN_BROWSER", "1") != "0"


# ---------------------------------------------------------------------------
# Path resolution — works in both dev and PyInstaller frozen mode
# ---------------------------------------------------------------------------
def get_base_dir() -> Path:
    """Return the directory that contains canvas-app.html and canvas-proxy.py."""
    if getattr(sys, "frozen", False):
        # PyInstaller bundles files into sys._MEIPASS
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).parent


def find_file(name: str) -> Path:
    p = get_base_dir() / name
    if p.exists():
        return p
    raise FileNotFoundError(f"Cannot locate {name!r} (looked in {get_base_dir()})")


# ---------------------------------------------------------------------------
# Port helpers
# ---------------------------------------------------------------------------
def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def find_free_port(start: int, max_tries: int = 20) -> int:
    for port in range(start, start + max_tries):
        if not is_port_in_use(port):
            return port
    raise RuntimeError(f"No free port found starting at {start}")


# ---------------------------------------------------------------------------
# Inline proxy handler (used when running frozen / in-process)
# ---------------------------------------------------------------------------
class _ProxyHandler(BaseHTTPRequestHandler):
    """Inline copy of the proxy logic so the launcher is self-contained."""

    def log_message(self, fmt, *args):  # silence default stderr logging
        log.debug("[proxy] %s %s → %s", self.command, self.path, args[1] if len(args) > 1 else "")

    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, X-Canvas-Domain, Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.end_headers()

    def do_GET(self):
        domain = self.headers.get("X-Canvas-Domain", "").strip()
        auth = self.headers.get("Authorization", "").strip()

        if not domain or not auth:
            self.send_response(400)
            self.send_cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps({"error": "Missing X-Canvas-Domain or Authorization header"}).encode()
            )
            return

        target = f"https://{domain}{self.path}"
        req = Request(target, headers={"Authorization": auth, "Accept": "application/json"})
        try:
            with urlopen(req, timeout=15) as resp:
                body = resp.read()
                self.send_response(resp.status)
                self.send_cors()
                self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                self.send_header("Link", resp.headers.get("Link", ""))
                self.end_headers()
                self.wfile.write(body)
        except HTTPError as e:
            body = e.read()
            self.send_response(e.code)
            self.send_cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        except URLError as e:
            self.send_response(502)
            self.send_cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e.reason)}).encode())


# ---------------------------------------------------------------------------
# Proxy startup
# ---------------------------------------------------------------------------
_proxy_proc = None  # type: subprocess.Popen | None
_proxy_server = None  # type: HTTPServer | None


def _run_proxy_in_thread():
    """Run the proxy server inline (used when frozen or when subprocess is unavailable)."""
    global _proxy_server
    _proxy_server = HTTPServer((PROXY_HOST, PROXY_PORT), _ProxyHandler)
    log.info("Proxy running in-process on %s:%d", PROXY_HOST, PROXY_PORT)
    _proxy_server.serve_forever()


def start_proxy(frozen: bool = False) -> bool:
    """Start the proxy.  Returns True if we started it (False if already running)."""
    global _proxy_proc

    if is_port_in_use(PROXY_PORT, PROXY_HOST):
        log.info("Proxy already running on %s:%d — reusing.", PROXY_HOST, PROXY_PORT)
        return False

    if frozen:
        # In PyInstaller mode there is no separate Python interpreter, so run in-thread.
        t = threading.Thread(target=_run_proxy_in_thread, daemon=True)
        t.start()
    else:
        # Development mode: spawn canvas-proxy.py as a separate process.
        proxy_script = find_file("canvas-proxy.py")
        env = os.environ.copy()
        env["CANVAS_PROXY_PORT"] = str(PROXY_PORT)
        env["CANVAS_PROXY_HOST"] = PROXY_HOST
        log.info("Starting proxy subprocess on %s:%d …", PROXY_HOST, PROXY_PORT)
        _proxy_proc = subprocess.Popen(
            [sys.executable, str(proxy_script)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        def _drain():
            for line in _proxy_proc.stdout:
                log.debug("[proxy] %s", line.rstrip())

        threading.Thread(target=_drain, daemon=True).start()

    # Wait up to 3 s for the port to open.
    for _ in range(30):
        if is_port_in_use(PROXY_PORT, PROXY_HOST):
            log.info("Proxy is ready.")
            return True
        time.sleep(0.1)

    log.warning("Proxy did not open port %d within 3 s — continuing anyway.", PROXY_PORT)
    return True


# ---------------------------------------------------------------------------
# Static UI server
# ---------------------------------------------------------------------------
_ui_server = None  # type: HTTPServer | None


class _UIHandler(SimpleHTTPRequestHandler):
    """Serve canvas-app.html (and any sibling files) silently."""

    _base = ""  # set before constructing the server

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=_UIHandler._base, **kwargs)

    def log_message(self, fmt, *args):
        pass  # suppress per-request output


def start_ui_server(ui_port: int, base_dir: Path) -> None:
    global _ui_server
    _UIHandler._base = str(base_dir)
    _ui_server = HTTPServer(("127.0.0.1", ui_port), _UIHandler)
    log.info("UI server on http://127.0.0.1:%d", ui_port)
    _ui_server.serve_forever()


# ---------------------------------------------------------------------------
# Status endpoint  (GET /launcher-status  → JSON health info)
# ---------------------------------------------------------------------------
class _StatusUIHandler(_UIHandler):
    """Extends the static handler with a /launcher-status JSON endpoint."""

    def do_GET(self):
        if self.path.rstrip("/") == "/launcher-status":
            payload = json.dumps(
                {
                    "launcher": True,
                    "proxy_port": PROXY_PORT,
                    "ui_port": self.server.server_address[1],
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            super().do_GET()


def start_ui_server_with_status(ui_port: int, base_dir: Path) -> None:
    global _ui_server
    _UIHandler._base = str(base_dir)
    _ui_server = HTTPServer(("127.0.0.1", ui_port), _StatusUIHandler)
    log.info("UI server on http://127.0.0.1:%d", ui_port)
    _ui_server.serve_forever()


# ---------------------------------------------------------------------------
# Shutdown
# ---------------------------------------------------------------------------
def _shutdown(signum=None, frame=None):
    log.info("Shutting down…")
    if _ui_server:
        threading.Thread(target=_ui_server.shutdown, daemon=True).start()
    if _proxy_server:
        threading.Thread(target=_proxy_server.shutdown, daemon=True).start()
    if _proxy_proc and _proxy_proc.poll() is None:
        _proxy_proc.terminate()
        try:
            _proxy_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _proxy_proc.kill()
    log.info("Goodbye.")
    sys.exit(0)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Canvas Study Help — Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser automatically")
    parser.add_argument("--enable-autostart", action="store_true", help="Enable start on login and exit")
    parser.add_argument("--disable-autostart", action="store_true", help="Disable start on login and exit")
    parser.add_argument("--autostart-status", action="store_true", help="Print autostart status and exit")
    args = parser.parse_args()

    # Handle autostart commands without starting the full app.
    if args.enable_autostart or args.disable_autostart or args.autostart_status:
        try:
            import autostart  # noqa: PLC0415

            if args.enable_autostart:
                autostart.enable()
            elif args.disable_autostart:
                autostart.disable()
            else:
                enabled = autostart.status()
                print(f"Autostart: {'enabled' if enabled else 'disabled'}")
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        return

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    log.info("=== Canvas Study Help — Launcher ===")

    frozen = getattr(sys, "frozen", False)

    # 1. Start proxy
    start_proxy(frozen=frozen)

    # 2. Find a free UI port
    ui_port = UI_PORT_DEFAULT if not is_port_in_use(UI_PORT_DEFAULT) else find_free_port(UI_PORT_DEFAULT)

    # 3. Locate HTML
    base_dir = get_base_dir()
    log.debug("Base dir: %s", base_dir)

    # 4. Start UI server in a background thread
    t = threading.Thread(
        target=start_ui_server_with_status, args=(ui_port, base_dir), daemon=True
    )
    t.start()
    time.sleep(0.3)  # let the server bind

    # 5. Open browser
    open_browser = OPEN_BROWSER and not args.no_browser
    url = f"http://127.0.0.1:{ui_port}/canvas-app.html"
    if open_browser:
        log.info("Opening browser → %s", url)
        webbrowser.open(url)
    else:
        log.info("UI available at %s", url)

    log.info("Press Ctrl+C to stop.")

    # 6. Keep running; restart proxy if it dies unexpectedly
    global _proxy_proc
    while True:
        time.sleep(2)
        if _proxy_proc and _proxy_proc.poll() is not None:
            log.warning("Proxy subprocess exited — restarting…")
            _proxy_proc = None
            start_proxy(frozen=False)


if __name__ == "__main__":
    main()
