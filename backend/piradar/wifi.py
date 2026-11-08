from __future__ import annotations

import logging
import os
import subprocess
import threading
from typing import Any, Callable


class WifiError(RuntimeError):
    """A safe, user-facing Wi-Fi error.

    ``detail`` holds NetworkManager's own wording (never the password), shown
    in small print under the message and written to the journal, so a failed
    connection can be diagnosed later.
    """

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.detail = detail


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


LOG = logging.getLogger("piradar.wifi")

# Shown when a WPA2/WPA3 mixed-mode router rejects the Pi. Pi 3 class Wi-Fi
# chips (brcmfmac) often fail this handshake even with the right password;
# scripts/wifi-compat.sh applies the known fix.
WPA3_HINT = "If it is right, this router's WPA3 mode is a known Pi 3 problem: turn on Wi-Fi compatibility mode."


class NetworkManagerWifi:
    """Small, dependency-free adapter for NetworkManager's nmcli client."""

    def __init__(
        self,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self._runner = runner
        self._lock = threading.RLock()
        self._visible: dict[str, dict[str, Any]] = {}

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
            self._visible = dict(by_ssid)
        return networks

    def connect(self, ssid: str, password: str) -> dict[str, Any]:
        if not isinstance(ssid, str) or not ssid or len(ssid.encode("utf-8")) > 32:
            raise WifiError("Select a valid network from the scan results.")
        if not isinstance(password, str) or len(password) > 256 or "\n" in password or "\r" in password:
            raise WifiError("The Wi-Fi password is invalid.")
        with self._lock:
            network = self._visible.get(ssid)
        if network is None:
            raise WifiError("That network is no longer in the scan results. Scan again.")
        security = str(network.get("security", ""))
        self._check_password_shape(security, password)
        if not network.get("connected"):
            self._forget_saved_profiles(ssid)

        command = ["nmcli", "--ask", "--wait", "30", "device", "wifi", "connect", ssid]
        try:
            self._run(command, timeout=35, input=f"{password}\n" if password else None)
        except WifiError as error:
            friendly = self._explain_failure(str(error), security)
            LOG.warning("Wi-Fi connect to %r (%s) failed: %s", ssid, security or "open", error)
            raise WifiError(friendly, detail=str(error)[:200]) from None
        return {"ssid": ssid, "connected": True}

    def _forget_saved_profiles(self, ssid: str) -> None:
        """Delete saved NetworkManager profiles for this network first.

        A failed attempt can leave a saved profile holding the wrong password.
        NetworkManager then keeps trying that stale key and reports "Secrets
        were required, but not provided" even when the new password is right.
        Clearing it means every attempt uses exactly what was just typed. Only
        profiles for this SSID are touched, and any problem here is logged and
        skipped rather than blocking the connection attempt.
        """
        try:
            listing = self._run(
                ["nmcli", "--terse", "--escape", "yes", "--fields", "UUID,TYPE", "connection", "show"],
                timeout=10,
            )
            for row in listing.stdout.splitlines():
                fields = _split_terse_row(row)
                if len(fields) != 2 or fields[1] not in {"802-11-wireless", "wifi"}:
                    continue
                uuid = fields[0]
                saved = self._run(
                    ["nmcli", "--escape", "no", "--get-values", "802-11-wireless.ssid", "connection", "show", uuid],
                    timeout=10,
                )
                if saved.stdout.rstrip("\n") == ssid:
                    self._run(["nmcli", "connection", "delete", uuid], timeout=15)
                    LOG.info("Removed saved Wi-Fi profile %s for %r before reconnecting", uuid, ssid)
        except WifiError as error:
            LOG.warning("Could not clear saved Wi-Fi profiles for %r: %s", ssid, error)

    @staticmethod
    def _check_password_shape(security: str, password: str) -> None:
        """Catch passwords that cannot be right before trying the router.

        WPA/WPA2/WPA3 personal passwords are 8 to 63 characters, or exactly
        64 hexadecimal digits. A typo here would otherwise look like a router
        problem after a 30 second wait.
        """
        if "WPA" not in security.upper() or not password:
            return
        if len(password) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in password):
            return
        length = len(password.encode("utf-8"))
        if length < 8 or length > 63:
            raise WifiError(
                f"Wi-Fi passwords are 8 to 63 characters long; this one is {len(password)}. Check it with the eye button."
            )

    @staticmethod
    def _explain_failure(detail: str, security: str) -> str:
        """Turn NetworkManager's error into advice someone can act on."""
        text = detail.lower()
        wpa3 = "WPA3" in security.upper()
        if "no network with ssid" in text or "not found" in text:
            return "That network has gone out of range. Move PiRadar closer to the router and scan again."
        if any(token in text for token in ("ip configuration", "dhcp", "ip4", "no address")):
            return "PiRadar joined the network but the router did not give it an address. Restart the router, or check it is not blocking new devices."
        if any(token in text for token in ("secret", "password", "psk", "authentication", "4-way", "handshake")):
            message = "Could not connect. Check the password with the eye button."
            return f"{message} {WPA3_HINT}" if wpa3 else message
        if "timeout" in text or "timed out" in text:
            message = "The router did not answer in time. Move PiRadar closer to the router and try again."
            return f"{message} {WPA3_HINT}" if wpa3 else message
        if "failed to connect" in text or "activation failed" in text or "supplicant" in text:
            message = "The router turned the connection down."
            return f"{message} {WPA3_HINT}" if wpa3 else f"{message} Check the password and try again."
        return "Could not connect to that network. Try again."

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
