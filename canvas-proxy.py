#!/usr/bin/env python3
"""
Canvas API Proxy — solves CORS when using Canvas AI Assistant

Run standalone:  python3 canvas-proxy.py
The launcher (launcher.py) starts this automatically — no manual step needed.

Environment variables:
    CANVAS_PROXY_PORT   Listening port  (default: 3001)
    CANVAS_PROXY_HOST   Listening host  (default: localhost)
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
import json
import os

PORT = int(os.environ.get("CANVAS_PROXY_PORT", "3001"))
HOST = os.environ.get("CANVAS_PROXY_HOST", "localhost")

class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"  {self.command} {self.path} → {args[1]}")

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
        auth   = self.headers.get("Authorization", "").strip()

        if not domain or not auth:
            self.send_response(400)
            self.send_cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Missing X-Canvas-Domain or Authorization header"}).encode())
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

if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), ProxyHandler)
    print(f"\n  Canvas Proxy running on http://{HOST}:{PORT}")
    print(f"  Open canvas-app.html in your browser (or use the launcher)\n")
    print(f"  Press Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Proxy stopped.")
