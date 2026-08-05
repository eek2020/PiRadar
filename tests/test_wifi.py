from __future__ import annotations

import subprocess
import unittest

from piradar.wifi import NetworkManagerWifi, WifiError, _split_terse_row


class RecordingRunner:
    def __init__(self, stdout: str = "", error: str | None = None) -> None:
        self.stdout = stdout
        self.error = error
        self.calls: list[tuple[list[str], dict]] = []

    def __call__(self, command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        self.calls.append((command, kwargs))
        if self.error is not None:
            raise subprocess.CalledProcessError(10, command, stderr=self.error)
        return subprocess.CompletedProcess(command, 0, stdout=self.stdout, stderr="")


class WifiTests(unittest.TestCase):
    def test_terse_parser_unescapes_colons_and_backslashes(self) -> None:
        self.assertEqual(_split_terse_row(r"*:Cafe\: Upstairs:82:WPA2"), ["*", "Cafe: Upstairs", "82", "WPA2"])
        self.assertEqual(_split_terse_row(r":Office\\Guest:45:--"), ["", r"Office\Guest", "45", "--"])

    def test_scan_deduplicates_and_orders_visible_networks(self) -> None:
        runner = RecordingRunner(
            ":Guest:40:--\n"
            ":Office:88:WPA2\n"
            "*:Current:62:WPA2\n"
            ":Office:30:WPA2\n"
            ":Hidden:bad:802.1X\n"
            ": :99:WPA2\n"
        )
        manager = NetworkManagerWifi(runner)

        networks = manager.scan()

        self.assertEqual([network["ssid"] for network in networks], ["Current", "Office", "Guest", "Hidden"])
        self.assertTrue(networks[0]["connected"])
        self.assertEqual(networks[1]["signal"], 88)
        self.assertFalse(networks[2]["secured"])
        self.assertFalse(networks[3]["supported"])

    def test_connect_only_accepts_an_ssid_from_the_latest_scan(self) -> None:
        runner = RecordingRunner(":Visible:75:WPA2\n")
        manager = NetworkManagerWifi(runner)
        manager.scan()

        with self.assertRaisesRegex(WifiError, "scan results"):
            manager.connect("Typed by hand", "password")

    def test_password_is_sent_on_stdin_and_not_in_process_arguments(self) -> None:
        runner = RecordingRunner(":Visible:75:WPA2\n")
        manager = NetworkManagerWifi(runner)
        manager.scan()
        secret = "correct horse battery staple"

        result = manager.connect("Visible", secret)

        command, kwargs = runner.calls[-1]
        self.assertEqual(result, {"ssid": "Visible", "connected": True})
        self.assertNotIn(secret, command)
        self.assertEqual(kwargs["input"], secret + "\n")
        self.assertIn("--ask", command)

    def test_authentication_errors_are_safe_for_the_ui(self) -> None:
        runner = RecordingRunner(":Visible:75:WPA2\n")
        manager = NetworkManagerWifi(runner)
        manager.scan()
        runner.error = "Error: Connection activation failed: Secrets were required"

        with self.assertRaisesRegex(WifiError, "Check the Wi-Fi password"):
            manager.connect("Visible", "wrong password")

    def test_password_cannot_inject_extra_interactive_answers(self) -> None:
        runner = RecordingRunner(":Visible:75:WPA2\n")
        manager = NetworkManagerWifi(runner)
        manager.scan()

        with self.assertRaisesRegex(WifiError, "password is invalid"):
            manager.connect("Visible", "first answer\nsecond answer")


if __name__ == "__main__":
    unittest.main()
