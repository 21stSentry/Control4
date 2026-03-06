#!/usr/bin/env python3
"""Control4 Audio Matrix web app (cross-platform local server)."""

from __future__ import annotations

import json
import re
import socket
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HOST = "0.0.0.0"
PORT = 8765
DEFAULT_MATRIX_IP = "192.168.1.151"
DEFAULT_MATRIX_PORT = 23
CONFIG_PATH = Path(__file__).with_name("matrix_config.json")
STATIC_DIR = Path(__file__).with_name("app_static")


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    zones = {str(i): 1 for i in range(1, 17)}
    presets = {
        "Input1-AllZones": {str(i): 1 for i in range(1, 17)},
        "Sequential": {str(i): i for i in range(1, 17)},
    }
    return {
        "device": {"host": DEFAULT_MATRIX_IP, "port": DEFAULT_MATRIX_PORT, "bind_ip": ""},
        "zones": zones,
        "presets": presets,
        "default_preset": "Input1-AllZones",
        "auto_apply_default_preset": True,
    }


def save_config(data: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


CONFIG_LOCK = threading.Lock()
STATE = load_config()


class TelnetMatrixClient:
    def __init__(
        self,
        host: str,
        port: int = DEFAULT_MATRIX_PORT,
        timeout: float = 2.5,
        bind_ip: str = "",
    ):
        self.host = host
        self.port = int(port)
        self.timeout = timeout
        self.bind_ip = bind_ip.strip()

    def _connect(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        if self.bind_ip:
            sock.bind((self.bind_ip, 0))
        sock.connect((self.host, self.port))
        return sock

    def fetch_banner(self) -> str:
        with self._connect() as sock:
            sock.settimeout(self.timeout)
            chunks = []
            while True:
                try:
                    data = sock.recv(4096)
                except socket.timeout:
                    break
                if not data:
                    break
                chunks.append(data)
                if len(data) < 4096:
                    break
            return b"".join(chunks).decode("utf-8", errors="ignore")

    def send_line(self, line: str) -> str:
        with self._connect() as sock:
            sock.settimeout(self.timeout)
            try:
                sock.recv(4096)
            except Exception:
                pass
            sock.sendall((line.rstrip("\n") + "\n").encode("utf-8"))
            chunks = []
            while True:
                try:
                    data = sock.recv(4096)
                except socket.timeout:
                    break
                if not data:
                    break
                chunks.append(data)
                if len(data) < 4096:
                    break
            return b"".join(chunks).decode("utf-8", errors="ignore")


def parse_banner(banner: str) -> dict:
    info = {
        "product": None,
        "firmware": None,
        "os": None,
        "mac": None,
        "ip": None,
        "gateway": None,
        "mask": None,
        "raw": banner,
    }
    patterns = {
        "product": r"^Product:\s*(.+)$",
        "firmware": r"^Firmware:\s*(.+)$",
        "os": r"^OS Version:\s*(.+)$",
        "mac": r"^MAC:\s*(.+)$",
        "ip": r"^IP Addr:\s*(.+)$",
        "gateway": r"^Gateway:\s*(.+)$",
        "mask": r"^Mask:\s*(.+)$",
    }
    for line in banner.splitlines():
        text = line.strip()
        for key, pat in patterns.items():
            m = re.match(pat, text, flags=re.IGNORECASE)
            if m:
                info[key] = m.group(1).strip()
    info["is_control4"] = (info.get("mac") or "").lower().startswith("00:0f:ff")
    return info


class AppHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        return

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(length) if length > 0 else b"{}"
        return json.loads(data.decode("utf-8"))

    def _send_json(self, payload: dict, status: int = 200) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _serve_static(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        ctype = "text/plain"
        if path.suffix == ".html":
            ctype = "text/html; charset=utf-8"
        elif path.suffix == ".css":
            ctype = "text/css; charset=utf-8"
        elif path.suffix == ".js":
            ctype = "application/javascript; charset=utf-8"
        raw = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json({"ok": True})
            return
        if parsed.path == "/api/config":
            with CONFIG_LOCK:
                self._send_json({"ok": True, "config": STATE})
            return
        if parsed.path == "/api/status":
            qs = parse_qs(parsed.query)
            host = (qs.get("host", [None])[0] or STATE["device"]["host"]).strip()
            port = int((qs.get("port", [None])[0] or STATE["device"]["port"]))
            bind_ip = (qs.get("bind_ip", [None])[0] or STATE["device"].get("bind_ip", "")).strip()
            try:
                client = TelnetMatrixClient(host, port, bind_ip=bind_ip)
                banner = client.fetch_banner()
                info = parse_banner(banner)
                self._send_json({"ok": True, "status": info})
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=502)
            return

        if parsed.path == "/" or parsed.path == "/index.html":
            return self._serve_static(STATIC_DIR / "index.html")
        if parsed.path.startswith("/"):
            maybe = STATIC_DIR / parsed.path.lstrip("/")
            if maybe.exists():
                return self._serve_static(maybe)
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            payload = self._read_json()
        except Exception:
            self._send_json({"ok": False, "error": "Invalid JSON"}, status=400)
            return

        if parsed.path == "/api/config":
            with CONFIG_LOCK:
                state = payload.get("config")
                if not isinstance(state, dict):
                    self._send_json({"ok": False, "error": "config object required"}, status=400)
                    return
                STATE.clear()
                STATE.update(state)
                save_config(STATE)
            self._send_json({"ok": True})
            return

        if parsed.path == "/api/route":
            zone = str(payload.get("zone", "")).strip()
            source = int(payload.get("source", 0))
            host = payload.get("host") or STATE["device"]["host"]
            port = int(payload.get("port") or STATE["device"]["port"])
            bind_ip = str(payload.get("bind_ip") or STATE["device"].get("bind_ip", "")).strip()
            if zone not in STATE.get("zones", {}):
                self._send_json({"ok": False, "error": "Unknown zone"}, status=400)
                return

            with CONFIG_LOCK:
                STATE["zones"][zone] = source
                save_config(STATE)

            # Attempt common CLI command; this firmware may be debug-only and ignore it.
            command = f"route {zone} {source}"
            response = ""
            success = True
            try:
                response = TelnetMatrixClient(host, port, bind_ip=bind_ip).send_line(command)
            except Exception as exc:
                success = False
                response = str(exc)

            self._send_json(
                {
                    "ok": success,
                    "applied": success,
                    "command": command,
                    "device_response": response,
                    "error": response if not success else "",
                    "note": "If device_response is empty, this firmware may not expose config CLI on port 23.",
                }
            )
            return

        if parsed.path == "/api/preset/apply":
            name = str(payload.get("name", "")).strip()
            with CONFIG_LOCK:
                preset = STATE.get("presets", {}).get(name)
                if not preset:
                    self._send_json({"ok": False, "error": "Preset not found"}, status=404)
                    return
                STATE["zones"] = {k: int(v) for k, v in preset.items()}
                save_config(STATE)
            self._send_json({"ok": True, "zones": STATE["zones"]})
            return

        if parsed.path == "/api/telnet/send":
            cmd = str(payload.get("command", "")).strip()
            host = payload.get("host") or STATE["device"]["host"]
            port = int(payload.get("port") or STATE["device"]["port"])
            bind_ip = str(payload.get("bind_ip") or STATE["device"].get("bind_ip", "")).strip()
            if not cmd:
                self._send_json({"ok": False, "error": "command required"}, status=400)
                return
            try:
                response = TelnetMatrixClient(host, port, bind_ip=bind_ip).send_line(cmd)
                self._send_json({"ok": True, "response": response})
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=502)
            return

        self._send_json({"ok": False, "error": "Not found"}, status=404)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"Control4 Matrix app running on http://127.0.0.1:{PORT}")
    print("To use from phone, open http://<your-pc-lan-ip>:8765 on the same network.")
    server.serve_forever()


if __name__ == "__main__":
    main()
