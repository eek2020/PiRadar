"""Safe shutdown and restart for the PiRadar appliance.

The service runs as the unprivileged ``piradar`` user, so it cannot power the
Pi off directly. ``systemctl poweroff`` / ``reboot`` hand the request to
systemd-logind, and ``polkit/50-piradar-power.rules`` allows exactly those two
actions for the ``piradar`` user and nothing else.
"""

from __future__ import annotations

import os
import subprocess
from typing import Callable


class PowerError(RuntimeError):
    """A safe, user-facing power operation error."""


class SystemPower:
    """Small adapter around ``systemctl`` for shutdown and restart."""

    # Only these two actions are ever accepted. Anything else is rejected
    # before a command is built, so callers cannot inject other verbs.
    COMMANDS: dict[str, list[str]] = {
        "poweroff": ["systemctl", "poweroff"],
        "reboot": ["systemctl", "reboot"],
    }

    def __init__(
        self,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self._runner = runner

    def request(self, action: str) -> dict[str, object]:
        command = self.COMMANDS.get(action)
        if command is None:
            raise PowerError("Choose shut down or restart.")
        environment = os.environ.copy()
        environment["LC_ALL"] = "C"
        try:
            # systemctl returns as soon as logind has accepted the request;
            # the actual shutdown then proceeds in the background.
            self._runner(
                command,
                text=True,
                capture_output=True,
                check=True,
                timeout=15,
                env=environment,
            )
        except FileNotFoundError:
            raise PowerError("Power control is unavailable on this device.") from None
        except subprocess.TimeoutExpired:
            raise PowerError("The power request timed out. Try again.") from None
        except subprocess.CalledProcessError as error:
            detail = (error.stderr or error.stdout or "").strip().lower()
            if "interactive authentication" in detail or "access denied" in detail or "not authorized" in detail:
                raise PowerError("Power control is not permitted. Re-run the installer to add the power rule.") from None
            raise PowerError("The Pi refused the power request.") from None
        return {"action": action, "accepted": True}
