"""An emulated PiRadar Pi, for rehearsing changes before they reach real hardware.

The real PiRadar backend never talks to NetworkManager, systemd or the boot
files directly: it calls them through small adapters that run commands
(``nmcli``, ``journalctl``, ``systemctl``) and read a few files. This module
plays the other side of that conversation. ``EmulatedPi.runner`` answers those
commands the way a Raspberry Pi 3 running Raspberry Pi OS would, against an
emulated router chosen by a scenario (see ``scenarios.py``).

What is emulated, and how faithfully:

* NetworkManager's command-line output formats are reproduced exactly, so
  PiRadar's real parsing code is exercised.
* Saved Wi-Fi profiles behave like NetworkManager's: a failed attempt leaves
  its profile saved, and a saved profile with a wrong key keeps failing with
  "Secrets were required, but not provided" even when a new, correct password
  is typed (the known stale-profile trap).
* Boot settings are two separate things, as on a real Pi: the boot line on
  disk (``cmdline.txt``) and the one the running kernel booted with
  (``/proc/cmdline``). A boot setting only takes effect after a restart.
* Router behaviour (which passwords and security modes work on a Pi 3) is
  decided by the scenario. Log lines are representative of what
  NetworkManager, wpa_supplicant and the brcmfmac driver write, not copies of
  a particular router's logs.

Nothing here touches the computer's own networking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import subprocess
import threading
import time
from typing import Any, Callable
import uuid

# The boot line from Eric's Pi, as written by Raspberry Pi Imager.
REAL_BOOT_LINE = (
    "console=serial0,115200 console=tty1 root=PARTUUID=7bac7b86-02 rootfstype=ext4 "
    "fsck.repair=yes rootwait quiet splash plymouth.ignore-serial-consoles "
    "ds=nocloud;i=rpi-imager-1785669459115 cfg80211.ieee80211_regdom=GB"
)
# Options the Pi's firmware adds to the running kernel's command line.
FIRMWARE_PREFIX = "coherent_pool=1M 8250.nr_uarts=1 snd_bcm2835.enable_headphones=0 bcm2708_fb.fbwidth=800 bcm2708_fb.fbheight=480"
COMPAT_OPTION = "brcmfmac.feature_disable=0x82000"
SECRETS_ERROR = "Error: Connection activation failed: Secrets were required, but not provided."


def _escape(value: str) -> str:
    """nmcli --terse --escape yes: backslash-escape ':' and '\\'."""
    return value.replace("\\", "\\\\").replace(":", "\\:")


@dataclass
class Network:
    """One Wi-Fi network as the Pi's radio sees it."""

    ssid: str
    security: str              # as nmcli shows it, e.g. "WPA2" or "WPA2 WPA3"
    signal: int = 72
    channel: int = 6
    rsn_flags: str = "pair_ccmp group_ccmp psk"
    bssid: str = "AA:BB:CC:11:22:33"

    @property
    def frequency(self) -> str:
        return f"{2407 + 5 * self.channel} MHz"


@dataclass
class Profile:
    """A saved NetworkManager connection profile."""

    uuid: str
    kind: str                  # "802-11-wireless" or "802-3-ethernet"
    ssid: str = ""
    psk: str = ""


@dataclass
class EmulatedPi:
    root: Path
    scenario: Any                                     # scenarios.Scenario
    board: str = "Raspberry Pi 3 Model B Rev 1.2"
    boot_line: list[str] = field(default_factory=lambda: REAL_BOOT_LINE.split())
    running_line: list[str] = field(default_factory=lambda: REAL_BOOT_LINE.split())
    profiles: dict[str, Profile] = field(default_factory=dict)
    connected: str | None = None
    powered: bool = True
    reboots: int = 0
    # Bumped whenever the emulated screen should reload (restart, power on).
    screen_epoch: int = 0
    journal: list[str] = field(default_factory=list)
    # Software update emulation: the "GitHub" side and what is installed.
    latest_sha: str = "a" * 40
    installed_sha: str = "a" * 40

    def __post_init__(self) -> None:
        self.lock = threading.RLock()
        (self.root / "boot").mkdir(parents=True, exist_ok=True)
        (self.root / "opt").mkdir(parents=True, exist_ok=True)
        (self.root / "state").mkdir(parents=True, exist_ok=True)
        # Ethernet is always plugged in, as at the neighbour's.
        wired = Profile(str(uuid.uuid4()), "802-3-ethernet")
        self.profiles[wired.uuid] = wired
        self.scenario.prepare(self)
        self._write_files()
        self._write_version()
        self.log("systemd[1]", "Startup finished (emulated Raspberry Pi 3).")

    # --- Files the real backend reads --------------------------------------
    @property
    def paths(self) -> dict[str, Any]:
        return {
            "model": str(self.root / "model"),
            "running_cmdline": str(self.root / "proc-cmdline"),
            "boot_cmdline": [str(self.root / "boot" / "cmdline.txt")],
            "kernel": str(self.root / "osrelease"),
        }

    def _write_files(self) -> None:
        (self.root / "model").write_bytes(self.board.encode() + b"\x00")
        (self.root / "osrelease").write_text("6.18.39+rpt-rpi-v8\n")
        (self.root / "boot" / "cmdline.txt").write_text(" ".join(self.boot_line) + "\n")
        (self.root / "proc-cmdline").write_text(f"{FIRMWARE_PREFIX} {' '.join(self.running_line)}\n")

    def _write_version(self) -> None:
        (self.root / "opt" / "VERSION.json").write_text(json.dumps({
            "ref": "fix/keyboard-case-and-symbols",
            "sha": self.installed_sha,
            "installed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }))

    # --- Emulated system log -------------------------------------------------
    def log(self, process: str, message: str) -> None:
        stamp = time.strftime("%b %d %H:%M:%S")
        with self.lock:
            self.journal.append(f"{stamp} planeradar {process}: {message}")
            del self.journal[:-400]

    # --- State the control panel can change --------------------------------
    def set_compat(self, enabled: bool) -> None:
        """Change the boot line on disk, as an update or wifi-compat.sh would."""
        with self.lock:
            has = COMPAT_OPTION in self.boot_line
            if enabled and not has:
                self.boot_line.append(COMPAT_OPTION)
            elif not enabled and has:
                self.boot_line.remove(COMPAT_OPTION)
            self._write_files()

    @property
    def compat_saved(self) -> bool:
        return COMPAT_OPTION in self.boot_line

    @property
    def compat_active(self) -> bool:
        return COMPAT_OPTION in self.running_line

    def reboot(self) -> None:
        """Restart: the running kernel picks up the boot line from disk."""
        with self.lock:
            self.log("systemd-logind[401]", "The system will reboot now!")
            self.running_line = list(self.boot_line)
            self.reboots += 1
            self.powered = True
            # NetworkManager reconnects to a saved network if it still works.
            previous, self.connected = self.connected, None
            if previous:
                profile = self._profile_for(previous)
                network = self.scenario.network(previous)
                if profile and network and self.scenario.outcome(self, network, profile.psk) is None:
                    self.connected = previous
            self._write_files()
            self.log("kernel", f"-- Boot {self.reboots} -- Linux version 6.18.39+rpt-rpi-v8 (emulated)")
            if self.compat_active:
                self.log("kernel", f"Kernel command line: ... {COMPAT_OPTION}")
            self.screen_epoch += 1

    def power_on(self) -> None:
        with self.lock:
            if not self.powered:
                self.reboot()

    def publish_update(self) -> None:
        """Pretend a new commit was pushed to GitHub."""
        with self.lock:
            self.latest_sha = uuid.uuid4().hex + uuid.uuid4().hex[:8]

    # --- The command dispatcher the real backend calls ------------------------
    def runner(self, command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        program = command[0]
        handlers: dict[str, Callable[[list[str], dict[str, Any]], str]] = {
            "nmcli": self._nmcli,
            "journalctl": self._journalctl,
            "systemctl": self._systemctl,
        }
        if program not in handlers:
            raise FileNotFoundError(program)
        if not self.powered:
            raise subprocess.CalledProcessError(1, command, stderr="Error: the emulated Pi is switched off.")
        stdout = handlers[program](command, kwargs)
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    # nmcli ---------------------------------------------------------------
    def _nmcli(self, command: list[str], kwargs: dict[str, Any]) -> str:
        args = command[1:]
        with self.lock:
            if args[-3:] == ["list", "--rescan", "yes"] or args[-3:] == ["device", "wifi", "list"]:
                return self._wifi_list(args)
            if args[-2:] == ["connection", "show"]:
                return "".join(f"{p.uuid}:{p.kind}\n" for p in self.profiles.values())
            if "--get-values" in args and "802-11-wireless.ssid" in args:
                profile = self.profiles.get(args[-1])
                if profile is None:
                    raise subprocess.CalledProcessError(10, command, stderr=f"Error: {args[-1]} - no such connection profile.")
                return profile.ssid + "\n"
            if args[:2] == ["connection", "delete"]:
                removed = self.profiles.pop(args[2], None)
                if removed is None:
                    raise subprocess.CalledProcessError(10, command, stderr="Error: unknown connection.")
                self.log("NetworkManager[612]", f"<info>  audit: op=\"connection-delete\" uuid=\"{removed.uuid}\" name=\"{removed.ssid}\" result=\"success\"")
                return f"Connection '{removed.ssid}' ({removed.uuid}) successfully deleted.\n"
            if "connect" in args and "wifi" in args:
                ssid = args[args.index("connect") + 1]
                password = (kwargs.get("input") or "").rstrip("\n")
                return self._connect(command, ssid, password)
        raise subprocess.CalledProcessError(2, command, stderr="Error: command not emulated.")

    def _wifi_list(self, args: list[str]) -> str:
        fields = args[args.index("--fields") + 1].split(",")
        rows = []
        for network in self.scenario.networks:
            values = {
                "IN-USE": "*" if network.ssid == self.connected else "",
                "SSID": network.ssid,
                "BSSID": network.bssid,
                "CHAN": str(network.channel),
                "FREQ": network.frequency,
                "SIGNAL": str(network.signal),
                "SECURITY": network.security,
                "WPA-FLAGS": "(none)",
                "RSN-FLAGS": network.rsn_flags,
            }
            rows.append(":".join(_escape(values[name]) for name in fields))
        return "\n".join(rows) + "\n"

    def _profile_for(self, ssid: str) -> Profile | None:
        return next((p for p in self.profiles.values() if p.kind == "802-11-wireless" and p.ssid == ssid), None)

    def _connect(self, command: list[str], ssid: str, password: str) -> str:
        network = self.scenario.network(ssid)
        if network is None:
            raise subprocess.CalledProcessError(10, command, stderr=f"Error: No network with SSID '{ssid}' found.")
        nm = "NetworkManager[612]"
        self.log(nm, f"<info>  device (wlan0): Activation: starting connection '{ssid}'")
        profile = self._profile_for(ssid)
        if profile is None:
            # nmcli creates a new profile holding the typed password.
            profile = Profile(str(uuid.uuid4()), "802-11-wireless", ssid, password)
            self.profiles[profile.uuid] = profile
        # The stale-profile trap: NetworkManager tries the saved key, and a
        # wrong saved key makes the attempt fail whatever was typed.
        key = profile.psk
        failure = self.scenario.outcome(self, network, key)
        if failure is None:
            self.connected = ssid
            self.log("wpa_supplicant[540]", f"wlan0: CTRL-EVENT-CONNECTED - Connection to {network.bssid.lower()} completed")
            self.log(nm, "<info>  device (wlan0): Activation: (wifi) Stage 2 of 5 (Device Configure) successful. Connected to wireless network")
            self.log(nm, "<info>  device (wlan0): state change: ip-config -> activated")
            return f"Device 'wlan0' successfully activated with '{profile.uuid}'.\n"
        self._log_failure(network, failure)
        # NetworkManager keeps the failed profile saved, wrong key and all.
        raise subprocess.CalledProcessError(4, command, stderr=self.scenario.FAILURE_MESSAGES[failure])

    def _log_failure(self, network: Network, failure: str) -> None:
        nm, wpa = "NetworkManager[612]", "wpa_supplicant[540]"
        self.log(nm, "<info>  device (wlan0): supplicant interface state: associating -> 4way_handshake")
        if failure == "wrong_key":
            self.log(wpa, "wlan0: WPA: 4-Way Handshake failed - pre-shared key may be incorrect")
            self.log(wpa, f'wlan0: CTRL-EVENT-SSID-TEMP-DISABLED id=0 ssid="{network.ssid}" auth_failures=1 duration=10 reason=WRONG_KEY')
        elif failure == "sae_offload":
            self.log("kernel", "brcmfmac: brcmf_cfg80211_connect: firmware handshake offload failed for this AP (emulated)")
            self.log(wpa, f'wlan0: CTRL-EVENT-SSID-TEMP-DISABLED id=0 ssid="{network.ssid}" auth_failures=1 duration=10 reason=WRONG_KEY')
        elif failure == "wpa3_only":
            self.log(wpa, "wlan0: SME: Trying to authenticate with SAE; driver does not support SAE (emulated)")
            self.log(wpa, f"wlan0: CTRL-EVENT-ASSOC-REJECT bssid={network.bssid.lower()} status_code=43")
        elif failure == "timeout":
            self.log(wpa, f"wlan0: CTRL-EVENT-ASSOC-REJECT bssid={network.bssid.lower()} status_code=1 timed_out=1")
        elif failure == "no_dhcp":
            self.log(nm, "<warn>  dhcp4 (wlan0): request timed out")
            self.log(nm, "<info>  device (wlan0): state change: ip-config -> failed (reason 'ip-config-unavailable')")
        self.log(nm, "<warn>  device (wlan0): Activation: (wifi) disconnected during association, asking for new key")
        self.log(nm, "<info>  device (wlan0): state change: need-auth -> failed (reason 'no-secrets')")

    # journalctl ------------------------------------------------------------
    def _journalctl(self, command: list[str], kwargs: dict[str, Any]) -> str:
        with self.lock:
            return "\n".join(self.journal[-200:]) + "\n"

    # systemctl -------------------------------------------------------------
    def _systemctl(self, command: list[str], kwargs: dict[str, Any]) -> str:
        args = [arg for arg in command[1:] if arg != "--no-block"]
        if args == ["reboot"]:
            # Give the screen a moment to show "Restarting…" first.
            threading.Timer(2.5, self.reboot).start()
            return ""
        if args == ["poweroff"]:
            def off() -> None:
                with self.lock:
                    self.powered = False
                    self.connected = None
                    self.screen_epoch += 1
            self.log("systemd-logind[401]", "System is powering down.")
            threading.Timer(2.5, off).start()
            return ""
        if args == ["start", "piradar-update.service"]:
            threading.Thread(target=self._run_update, daemon=True).start()
            return ""
        return ""

    # Software update emulation --------------------------------------------
    @property
    def status_file(self) -> Path:
        return self.root / "update-status.json"

    def _status(self, state: str, message: str) -> None:
        self.status_file.write_text(json.dumps({
            "state": state, "message": message, "ref": "fix/keyboard-case-and-symbols", "sha": self.latest_sha,
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }))

    def _run_update(self) -> None:
        """Walk through the real updater's stages, a little faster."""
        if self.latest_sha == self.installed_sha:
            self._status("up_to_date", "Already up to date")
            return
        short = self.latest_sha[:7]
        for state, message, pause in (
            ("downloading", f"Downloading {short}", 1.5),
            ("testing", "Running tests", 3.0),
            ("installing", "Installing", 1.5),
            ("restarting", "Restarting PiRadar", 1.5),
        ):
            self._status(state, message)
            time.sleep(pause)
        with self.lock:
            self.installed_sha = self.latest_sha
            self._write_version()
            self.screen_epoch += 1      # the kiosk restarts on the new version
        if self.compat_saved and not self.compat_active:
            self._status("success", f"Updated to {short}. Restarting the Pi to finish")
            threading.Timer(2.0, self.reboot).start()
        else:
            self._status("success", f"Updated to {short}")

    def github(self, url: str) -> dict[str, Any]:
        """Stands in for the GitHub API calls the update manager makes."""
        if "/compare/" in url:
            return {"status": "identical" if self.latest_sha == self.installed_sha else "ahead"}
        return {"sha": self.latest_sha, "commit": {
            "message": "Emulated update\n\nPublished from the emulator control panel",
            "committer": {"date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
        }}
