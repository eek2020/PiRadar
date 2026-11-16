from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

from piradar.power import PowerError, SystemPower


class RecordingRunner:
    """Stands in for subprocess.run and records the command it was given."""

    def __init__(self, error: Exception | None = None) -> None:
        self.commands: list[list[str]] = []
        self.error = error

    def __call__(self, command, **kwargs):
        self.commands.append(command)
        if self.error:
            raise self.error
        return subprocess.CompletedProcess(command, 0, "", "")


class PowerTests(unittest.TestCase):
    def test_shutdown_and_restart_map_to_systemctl(self) -> None:
        runner = RecordingRunner()
        power = SystemPower(runner)
        self.assertEqual(power.request("poweroff"), {"action": "poweroff", "accepted": True})
        power.request("reboot")
        self.assertEqual(runner.commands, [["systemctl", "poweroff"], ["systemctl", "reboot"]])

    def test_unknown_actions_never_reach_the_shell(self) -> None:
        runner = RecordingRunner()
        power = SystemPower(runner)
        for action in ("halt", "poweroff --force", "", "suspend"):
            with self.assertRaises(PowerError):
                power.request(action)
        self.assertEqual(runner.commands, [])

    def test_missing_permission_gives_a_clear_message(self) -> None:
        denied = subprocess.CalledProcessError(1, ["systemctl"], stderr="Interactive authentication required.")
        with self.assertRaisesRegex(PowerError, "installer"):
            SystemPower(RecordingRunner(denied)).request("poweroff")

    def test_installer_ships_the_power_rule(self) -> None:
        root = Path(__file__).resolve().parents[1]
        rule = (root / "polkit" / "50-piradar-power.rules").read_text()
        self.assertIn('subject.user === "piradar"', rule)
        self.assertIn("org.freedesktop.login1.power-off", rule)
        self.assertIn("50-piradar-power.rules", (root / "scripts" / "install.sh").read_text())


if __name__ == "__main__":
    unittest.main()
