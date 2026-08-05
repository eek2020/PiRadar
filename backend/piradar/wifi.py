from __future__ import annotations

import os
import subprocess
import threading
from typing import Any, Callable


class WifiError(RuntimeError):
    """A safe, user-facing Wi-Fi operation error."""


def _split_terse_row(row: str) -> list[str]:
    fields: list[str] = []
    current: list[str] = []
    escaped = False
    for character in row:
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == ":":
            fields.append("".join(current))
            current = []
        else:
            current.append(character)
    if escaped:
        current.append("\\")
    fields.append("".join(current))
    return fields


class NetworkManagerWifi:
    """Small, dependency-free adapter for NetworkManager's nmcli client."""

    def __init__(
        self,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self._runner = runner
        self._lock = threading.RLock()
        self._visible_ssids: set[str] = set()

    def scan(self) -> list[dict[str, Any]]:
        result = self._run(
            [
                "nmcli",
                "--terse",
                "--escape",
                "yes",
                "--fields",
                "IN-USE,SSID,SIGNAL,SECURITY",
                "device",
                "wifi",
                "list",
                "--rescan",
                "yes",
            ],
            timeout=15,
        )
        by_ssid: dict[str, dict[str, Any]] = {}
        for row in result.stdout.splitlines():
            fields = _split_terse_row(row)
            if len(fields) != 4:
                continue
            in_use, ssid, signal_text, security = fields
            ssid = ssid.strip()
            if not ssid:
                continue
            try:
                signal = max(0, min(100, int(signal_text)))
            except ValueError:
                signal = 0
            security = security.strip()
            network = {
                "ssid": ssid,
                "signal": signal,
                "security": "Open" if security in {"", "--"} else security,
                "secured": security not in {"", "--"},
                "connected": in_use.strip().lower() in {"*", "yes"},
                "supported": "802.1x" not in security.lower() and "enterprise" not in security.lower(),
            }
            previous = by_ssid.get(ssid)
            if previous is None or network["connected"] or signal > previous["signal"]:
                by_ssid[ssid] = network

        networks = sorted(
            by_ssid.values(),
            key=lambda network: (not network["connected"], -network["signal"], network["ssid"].casefold()),
        )
        with self._lock:
            self._visible_ssids = set(by_ssid)
        return networks

    def connect(self, ssid: str, password: str) -> dict[str, Any]:
        if not isinstance(ssid, str) or not ssid or len(ssid.encode("utf-8")) > 32:
            raise WifiError("Select a valid network from the scan results.")
        if not isinstance(password, str) or len(password) > 256 or "\n" in password or "\r" in password:
            raise WifiError("The Wi-Fi password is invalid.")
        with self._lock:
            if ssid not in self._visible_ssids:
                raise WifiError("That network is no longer in the scan results. Scan again.")

        command = ["nmcli", "--ask", "--wait", "30", "device", "wifi", "connect", ssid]
        try:
            self._run(command, timeout=35, input=f"{password}\n" if password else None)
        except WifiError as error:
            message = str(error).lower()
            if any(token in message for token in ("secret", "password", "authentication", "failed to connect")):
                raise WifiError("Could not connect. Check the Wi-Fi password and try again.") from None
            raise
        return {"ssid": ssid, "connected": True}

    def _run(self, command: list[str], timeout: int, input: str | None = None) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["LC_ALL"] = "C"
        try:
            return self._runner(
                command,
                input=input,
                text=True,
                capture_output=True,
                check=True,
                timeout=timeout,
                env=environment,
            )
        except FileNotFoundError:
            raise WifiError("Wi-Fi management is unavailable on this device.") from None
        except subprocess.TimeoutExpired:
            raise WifiError("The Wi-Fi operation timed out. Try again.") from None
        except subprocess.CalledProcessError as error:
            detail = (error.stderr or error.stdout or "NetworkManager rejected the request.").strip()
            raise WifiError(detail) from None
