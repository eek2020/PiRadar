"""Over-the-air software updates, driven from the touchscreen.

The app itself never installs anything. It only:

* reads what is installed (``/opt/piradar/VERSION.json``, written by
  ``scripts/update.sh``) and the updater's progress file;
* asks GitHub for the newest commit on the channel the Pi follows;
* starts ``piradar-update.service``, which polkit allows for the piradar user
  and nothing else; the updater runs as root under systemd and applies its
  own tests, backup, health check and rollback;
* stores the "install updates automatically" switch (on unless switched
  off), which ``piradar-update-auto.service`` reads every 15 minutes.
"""

from __future__ import annotations

import calendar
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
from typing import Any, Callable
from urllib.parse import quote
from urllib.request import Request, urlopen

from piradar import __version__


class UpdateError(RuntimeError):
    """A safe, user-facing update error."""


# Updater states that mean "an update is in progress".
RUNNING_STATES = {"checking", "downloading", "testing", "installing", "restarting", "rolling_back"}
# A progress file older than this is treated as stale (the run was killed).
RUN_TIMEOUT_SECONDS = 25 * 60
# How long a GitHub answer is reused, to stay well inside the API rate limit.
CHECK_CACHE_SECONDS = 5 * 60


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _parse_time(value: Any) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        return float(calendar.timegm(time.strptime(value, "%Y-%m-%dT%H:%M:%SZ")))
    except ValueError:
        return None


class UpdateManager:
    def __init__(
        self,
        state_dir: str | Path,
        *,
        repo: str = os.getenv("PIRADAR_UPDATE_REPO", "eek2020/PiRadar"),
        install_dir: str | Path = "/opt/piradar",
        channel_file: str | Path = "/etc/piradar/update-channel",
        status_file: str | Path = "/var/lib/piradar-update/status.json",
        fetch: Callable[[str], dict[str, Any]] | None = None,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.repo = repo
        self.install_dir = Path(install_dir)
        self.channel_file = Path(channel_file)
        self.status_file = Path(status_file)
        self.settings_file = Path(state_dir) / "update-settings.json"
        self._fetch = fetch or self._fetch_github
        self._runner = runner
        self._clock = clock
        self._lock = threading.RLock()
        self._cached: tuple[float, str, dict[str, Any]] | None = None

    # --- What is installed, and what the updater is doing --------------------
    def channel(self) -> str:
        try:
            value = self.channel_file.read_text(encoding="utf-8").strip()
        except OSError:
            value = ""
        return value or "main"

    def installed(self) -> dict[str, Any]:
        version = _read_json(self.install_dir / "VERSION.json")
        sha = version.get("sha") if isinstance(version.get("sha"), str) else ""
        return {
            # The running code's own version number, e.g. "0.2.0".
            "version": __version__,
            "ref": version.get("ref") or None,
            "sha": sha or None,
            "short": sha[:7] or None,
            "installed_at": version.get("installed_at"),
        }

    def progress(self) -> dict[str, Any]:
        status = _read_json(self.status_file)
        state = status.get("state") if isinstance(status.get("state"), str) else "idle"
        running = state in RUNNING_STATES
        started = _parse_time(status.get("at"))
        if running and started is not None and self._clock() - started > RUN_TIMEOUT_SECONDS:
            # The updater was interrupted (for example by a power cut).
            state, running = "interrupted", False
        return {"state": state, "running": running, "message": status.get("message"), "at": status.get("at")}

    def auto_enabled(self) -> bool:
        # On unless someone has switched it off, so a Pi given to someone else
        # keeps updating itself with nobody at it.
        return _read_json(self.settings_file).get("auto") is not False

    def status(self) -> dict[str, Any]:
        with self._lock:
            cached = self._cached[2] if self._cached and self._cached[1] == self.channel() else None
        return {
            "channel": self.channel(),
            "installed": self.installed(),
            "progress": self.progress(),
            "auto": self.auto_enabled(),
            "latest": cached,
            "available": self._available(cached),
        }

    # --- Actions ---------------------------------------------------------
    def check(self, force: bool = False) -> dict[str, Any]:
        """Ask GitHub for the newest commit on the channel."""
        channel = self.channel()
        with self._lock:
            if (
                not force
                and self._cached
                and self._cached[1] == channel
                and self._clock() - self._cached[0] < CHECK_CACHE_SECONDS
            ):
                return self.status()
        try:
            payload = self._fetch(
                f"https://api.github.com/repos/{quote(self.repo, safe='/')}/commits/{quote(channel, safe='/')}"
            )
        except Exception as error:  # network, HTTP or JSON problems
            raise UpdateError("Could not reach GitHub. Check the Pi is online.") from error
        sha = payload.get("sha")
        commit = payload.get("commit") if isinstance(payload.get("commit"), dict) else {}
        if not isinstance(sha, str) or len(sha) < 7:
            raise UpdateError(f"GitHub has no '{channel}' to update from.")
        message = commit.get("message") if isinstance(commit.get("message"), str) else ""
        committer = commit.get("committer") if isinstance(commit.get("committer"), dict) else {}
        latest = {
            "sha": sha,
            "short": sha[:7],
            "summary": message.splitlines()[0][:120] if message else "",
            "date": committer.get("date"),
            "direction": self._direction(sha),
        }
        with self._lock:
            self._cached = (self._clock(), channel, latest)
        return self.status()

    def install(self) -> dict[str, Any]:
        """Start the updater. It runs on its own and survives this service restarting."""
        if self.progress()["running"]:
            raise UpdateError("An update is already running.")
        try:
            self._runner(
                # --no-block: the updater restarts this very service, so the
                # request must not wait for it to finish.
                ["systemctl", "start", "--no-block", "piradar-update.service"],
                text=True,
                capture_output=True,
                check=True,
                timeout=15,
            )
        except FileNotFoundError:
            raise UpdateError("Updates are unavailable on this device.") from None
        except subprocess.TimeoutExpired:
            raise UpdateError("Starting the update timed out. Try again.") from None
        except subprocess.CalledProcessError:
            raise UpdateError("The Pi refused to start the update. Re-run the installer to add the update rule.") from None
        return self.status()

    def set_auto(self, enabled: bool) -> dict[str, Any]:
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(dir=self.settings_file.parent)
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump({"auto": bool(enabled)}, stream)
        # Root's nightly updater must be able to read this file.
        os.chmod(temporary, 0o644)
        os.replace(temporary, self.settings_file)
        return self.status()

    # --- Helpers -----------------------------------------------------------
    def _direction(self, latest_sha: str) -> str:
        """How the channel's newest commit relates to what is installed.

        "ahead" means a genuine update. "behind" means installing it would
        go back to an older version, which is never offered.
        """
        installed = self.installed()["sha"]
        if not installed:
            return "unknown-install"
        if installed == latest_sha:
            return "identical"
        try:
            payload = self._fetch(
                f"https://api.github.com/repos/{quote(self.repo, safe='/')}/compare/{installed}...{latest_sha}"
            )
        except Exception:
            # GitHub answered the commit lookup a moment ago, so a failure here
            # means it does not know the installed commit (for example its
            # branch was deleted). That cannot be shown to be newer, so offer
            # the update rather than blocking updates for ever.
            return "unknown-install"
        status = payload.get("status")
        if status not in {"ahead", "behind", "identical", "diverged"}:
            raise UpdateError("GitHub gave an unexpected comparison.")
        return status

    def _available(self, latest: dict[str, Any] | None) -> bool | None:
        if not latest:
            return None
        if latest["sha"] == self.installed()["sha"]:
            return False
        return latest.get("direction") in {"ahead", "diverged", "unknown-install"}

    @staticmethod
    def _fetch_github(url: str) -> dict[str, Any]:
        request = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "PiRadar-updater"})
        with urlopen(request, timeout=10) as response:
            payload = json.load(response)
        if not isinstance(payload, dict):
            raise ValueError("unexpected GitHub response")
        return payload
