#!/usr/bin/env python3
"""PiRadar emulator: rehearse changes on an emulated Pi before pushing them.

Runs the real PiRadar backend and touchscreen interface on this computer,
with NetworkManager, systemd, the system log and the boot files emulated by
``emulator/device.py`` and the router chosen from ``emulator/scenarios.py``.

    ./emulate                       # default scenario (your neighbour's symptom)
    ./emulate --scenario wpa3-mixed
    ./emulate --list                # show the scenarios

Opens a control page in the browser: the emulated 800x480 screen on the
left, and on the right the scenario, restart / power buttons, Wi-Fi
compatibility mode, "publish an update", and the emulated Pi's system log.
Every emulated Wi-Fi network uses the password radar-test-1.

Nothing touches this computer's own Wi-Fi or system settings; all emulated
state lives in a temporary folder that is deleted on exit.
"""

from __future__ import annotations

import sys

if sys.version_info < (3, 11):
    sys.exit(
        "PiRadar needs Python 3.11 or newer (this is %d.%d).\n"
        "On a Mac: install it from https://www.python.org/downloads/ or with "
        "Homebrew (brew install python), then run ./emulate again." % sys.version_info[:2]
    )

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from emulator.device import EmulatedPi  # noqa: E402
from emulator.scenarios import PASSWORD, SCENARIOS  # noqa: E402
from piradar.app import create_server  # noqa: E402
from piradar.config import Config  # noqa: E402
from piradar.power import SystemPower  # noqa: E402
from piradar.updates import UpdateManager  # noqa: E402
from piradar.wifi import NetworkManagerWifi  # noqa: E402

CONTROL_PAGE = Path(__file__).with_name("control.html")


class Emulator:
    """Holds the emulated Pi and the real PiRadar server running on top of it."""

    def __init__(self, scenario: str, port: int) -> None:
        self.port = port
        self.folder = tempfile.TemporaryDirectory(prefix="piradar-emulator-")
        self.server: ThreadingHTTPServer | None = None
        self.load(scenario)

    def load(self, scenario: str) -> None:
        """(Re)build the emulated Pi for a scenario and serve PiRadar on it."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        root = Path(self.folder.name) / scenario
        root.mkdir(parents=True, exist_ok=True)
        self.pi = EmulatedPi(root, SCENARIOS[scenario])

        # The real adapters, pointed at the emulated Pi.
        wifi = NetworkManagerWifi(self.pi.runner)
        wifi.paths = self.pi.paths
        updates = UpdateManager(
            root / "state",
            install_dir=root / "opt",
            channel_file=root / "update-channel",
            status_file=self.pi.status_file,
            fetch=self.pi.github,
            runner=self.pi.runner,
        )
        config = Config(port=self.port, provider="mock", state_dir=str(root / "state"))
        self.server = create_server(
            config,
            frontend_dir=ROOT / "frontend",
            wifi_manager=wifi,
            power=SystemPower(self.pi.runner),
            updates=updates,
        )
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def state(self) -> dict[str, object]:
        pi = self.pi
        with pi.lock:
            return {
                "scenario": pi.scenario.name,
                "summary": pi.scenario.summary,
                "notes": pi.scenario.notes,
                "scenarios": {name: s.summary for name, s in SCENARIOS.items()},
                "password": PASSWORD,
                "board": pi.board,
                "powered": pi.powered,
                "connected": pi.connected,
                "reboots": pi.reboots,
                "screen_epoch": pi.screen_epoch,
                "compat_saved": pi.compat_saved,
                "compat_active": pi.compat_active,
                "profiles": [p.ssid for p in pi.profiles.values() if p.kind == "802-11-wireless"],
                "update_available": pi.latest_sha != pi.installed_sha,
                "installed": pi.installed_sha[:7],
                "journal": pi.journal[-60:],
                "screen_url": f"http://127.0.0.1:{self.port}/",
            }

    def act(self, action: str, value: str | None) -> None:
        pi = self.pi
        if action == "scenario" and value in SCENARIOS:
            self.load(value)
        elif action == "restart":
            pi.reboot()
        elif action == "power_on":
            pi.power_on()
        elif action == "compat_on":
            pi.set_compat(True)
        elif action == "compat_off":
            pi.set_compat(False)
        elif action == "publish":
            pi.publish_update()
        elif action == "forget_wifi":
            with pi.lock:
                for key in [k for k, p in pi.profiles.items() if p.kind == "802-11-wireless"]:
                    del pi.profiles[key]
                pi.connected = None
        else:
            raise ValueError(f"unknown action {action!r}")


def control_handler(emulator: Emulator) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: object) -> None:  # keep the terminal quiet
            pass

        def _send(self, status: HTTPStatus, body: bytes, kind: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/":
                self._send(HTTPStatus.OK, CONTROL_PAGE.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/state":
                self._send(HTTPStatus.OK, json.dumps(emulator.state()).encode(), "application/json")
            else:
                self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")

        def do_POST(self) -> None:
            if self.path != "/action":
                self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                emulator.act(payload.get("action", ""), payload.get("value"))
            except (ValueError, json.JSONDecodeError) as error:
                self._send(HTTPStatus.BAD_REQUEST, json.dumps({"error": str(error)}).encode(), "application/json")
                return
            self._send(HTTPStatus.OK, json.dumps(emulator.state()).encode(), "application/json")

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PiRadar on an emulated Pi and router.")
    parser.add_argument("--scenario", default="neighbour", choices=sorted(SCENARIOS))
    parser.add_argument("--port", type=int, default=8090, help="port for the emulated screen (control page uses port+1)")
    parser.add_argument("--list", action="store_true", help="list the scenarios and exit")
    parser.add_argument("--no-browser", action="store_true", help="do not open the browser")
    args = parser.parse_args()

    if args.list:
        for name, scenario in SCENARIOS.items():
            print(f"{name:12} {scenario.summary}")
        return

    emulator = Emulator(args.scenario, args.port)
    control = ThreadingHTTPServer(("127.0.0.1", args.port + 1), control_handler(emulator))
    url = f"http://127.0.0.1:{args.port + 1}/"
    print(f"PiRadar emulator running: {url}")
    print(f"Scenario: {args.scenario}. Every emulated Wi-Fi password is {PASSWORD}. Ctrl+C to stop.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        control.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping the emulator.")
    finally:
        emulator.folder.cleanup()


if __name__ == "__main__":
    main()
