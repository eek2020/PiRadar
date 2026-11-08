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


class ScriptedRunner:
    """Answers each nmcli command by its arguments, like a small NetworkManager."""

    def __init__(self, scan: str, profiles: dict[str, tuple[str, str]], list_fails: bool = False) -> None:
        self.scan = scan
        self.profiles = profiles  # uuid -> (type, ssid)
        self.list_fails = list_fails
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        if "list" in command:
            return subprocess.CompletedProcess(command, 0, stdout=self.scan, stderr="")
        if command[-2:] == ["connection", "show"]:
            if self.list_fails:
                raise subprocess.CalledProcessError(1, command, stderr="Error: NetworkManager is not running.")
            rows = "".join(f"{uuid}:{kind}\n" for uuid, (kind, _) in self.profiles.items())
            return subprocess.CompletedProcess(command, 0, stdout=rows, stderr="")
        if "--get-values" in command:
            return subprocess.CompletedProcess(command, 0, stdout=self.profiles[command[-1]][1] + "\n", stderr="")
        if command[1:3] == ["connection", "delete"]:
            self.profiles.pop(command[3])
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


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

        with self.assertRaisesRegex(WifiError, "Check the password"):
            manager.connect("Visible", "wrong password")

    def test_password_cannot_inject_extra_interactive_answers(self) -> None:
        runner = RecordingRunner(":Visible:75:WPA2\n")
        manager = NetworkManagerWifi(runner)
        manager.scan()

        with self.assertRaisesRegex(WifiError, "password is invalid"):
            manager.connect("Visible", "first answer\nsecond answer")


    def _manager(self, security: str = "WPA2") -> tuple[NetworkManagerWifi, RecordingRunner]:
        runner = RecordingRunner(f":Home:75:{security}\n")
        manager = NetworkManagerWifi(runner)
        manager.scan()
        return manager, runner

    def test_impossible_password_lengths_are_caught_before_trying(self) -> None:
        manager, runner = self._manager("WPA2")
        calls_after_scan = len(runner.calls)
        with self.assertRaisesRegex(WifiError, "8 to 63 characters long; this one is 7"):
            manager.connect("Home", "short12")
        with self.assertRaisesRegex(WifiError, "8 to 63"):
            manager.connect("Home", "x" * 64)
        self.assertEqual(len(runner.calls), calls_after_scan, "router should not be contacted")
        manager.connect("Home", "a1" * 32)  # 64 hex digits is a valid raw key

    def test_wpa3_mixed_mode_failure_points_at_compatibility_mode(self) -> None:
        manager, runner = self._manager("WPA2 WPA3")
        runner.error = "Error: Connection activation failed: Secrets were required, but not provided"
        with self.assertRaises(WifiError) as raised:
            manager.connect("Home", "correct password")
        self.assertIn("compatibility mode", str(raised.exception))
        self.assertIn("Secrets were required", raised.exception.detail)

    def test_wpa2_password_failure_does_not_mention_wpa3(self) -> None:
        manager, runner = self._manager("WPA2")
        runner.error = "Error: Connection activation failed: Secrets were required, but not provided"
        with self.assertRaises(WifiError) as raised:
            manager.connect("Home", "wrong password")
        self.assertNotIn("WPA3", str(raised.exception))

    def test_other_failures_get_actionable_messages(self) -> None:
        cases = {
            "Error: Connection activation failed: IP configuration could not be reserved": "did not give it an address",
            "Error: Timeout expired (30 seconds)": "did not answer in time",
            "Error: No network with SSID 'Home' found.": "out of range",
        }
        for detail, expected in cases.items():
            manager, runner = self._manager("WPA2")
            runner.error = detail
            with self.assertRaisesRegex(WifiError, expected):
                manager.connect("Home", "good password")


    def test_stale_profile_for_the_network_is_cleared_before_connecting(self) -> None:
        runner = ScriptedRunner(
            ":Home:75:WPA2\n",
            {"aaa-1": ("802-11-wireless", "Home"), "bbb-2": ("802-11-wireless", "Office"), "ccc-3": ("802-3-ethernet", "")},
        )
        manager = NetworkManagerWifi(runner)
        manager.scan()
        manager.connect("Home", "good password")
        deletes = [c for c in runner.commands if c[1:3] == ["connection", "delete"]]
        self.assertEqual(deletes, [["nmcli", "connection", "delete", "aaa-1"]])
        self.assertIn("bbb-2", runner.profiles, "other networks' profiles are kept")
        self.assertIn("ccc-3", runner.profiles, "the Ethernet profile is kept")
        # The fresh attempt comes after the clean-up.
        self.assertIn("connect", runner.commands[-1])

    def test_profile_clean_up_problems_never_block_connecting(self) -> None:
        runner = ScriptedRunner(":Home:75:WPA2\n", {}, list_fails=True)
        manager = NetworkManagerWifi(runner)
        manager.scan()
        self.assertEqual(manager.connect("Home", "good password"), {"ssid": "Home", "connected": True})

    def test_the_network_in_use_is_not_deleted(self) -> None:
        runner = ScriptedRunner("*:Home:75:WPA2\n", {"aaa-1": ("802-11-wireless", "Home")})
        manager = NetworkManagerWifi(runner)
        manager.scan()
        manager.connect("Home", "good password")
        self.assertIn("aaa-1", runner.profiles)


if __name__ == "__main__":
    unittest.main()
