"""PiRadar's real Wi-Fi code against the emulated Pi and router scenarios.

These pin down both halves: that each scenario behaves as documented, and
that PiRadar copes with each one (clear advice, stale profile clean-up,
compatibility mode only working after a restart, diagnostics telling the truth).
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from emulator.device import EmulatedPi  # noqa: E402
from emulator.scenarios import PASSWORD, SCENARIOS  # noqa: E402
from piradar.wifi import NetworkManagerWifi, WifiError  # noqa: E402


class EmulatorScenarioTests(unittest.TestCase):
    def start(self, scenario: str) -> tuple[EmulatedPi, NetworkManagerWifi]:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        pi = EmulatedPi(Path(folder.name), SCENARIOS[scenario])
        wifi = NetworkManagerWifi(pi.runner)
        wifi.paths = pi.paths
        wifi.scan()
        return pi, wifi

    def test_home_router_connects_with_the_right_password_only(self) -> None:
        pi, wifi = self.start("home")
        with self.assertRaisesRegex(WifiError, "Check the password"):
            wifi.connect("Home-Hub", "wrong-password")
        # The failed attempt left a stale profile; PiRadar clears it first.
        self.assertEqual(wifi.connect("Home-Hub", PASSWORD), {"ssid": "Home-Hub", "connected": True})
        self.assertEqual(pi.connected, "Home-Hub")

    def test_neighbour_symptom_is_fixed_by_clearing_the_stale_profile(self) -> None:
        pi, wifi = self.start("neighbour")
        self.assertIn("Neighbour-Hub", [p.ssid for p in pi.profiles.values()])
        self.assertEqual(wifi.connect("Neighbour-Hub", PASSWORD)["connected"], True)

    def test_wpa3_mixed_needs_compat_mode_and_a_restart(self) -> None:
        pi, wifi = self.start("wpa3-mixed")
        with self.assertRaises(WifiError) as raised:
            wifi.connect("BT-Hub", PASSWORD)
        self.assertIn("compatibility mode", str(raised.exception))

        pi.set_compat(True)          # what an update does
        with self.assertRaises(WifiError):
            wifi.connect("BT-Hub", PASSWORD)   # saved, not yet active
        self.assertIn("saved on · active off", "\n".join(wifi.diagnostics("BT-Hub")["lines"]))

        pi.reboot()
        wifi.scan()
        self.assertEqual(wifi.connect("BT-Hub", PASSWORD)["connected"], True)
        self.assertIn("saved on · active on", "\n".join(wifi.diagnostics("BT-Hub")["lines"]))

    def test_wpa3_only_never_works_on_a_pi3(self) -> None:
        pi, wifi = self.start("wpa3-only")
        pi.set_compat(True)
        pi.reboot()
        wifi.scan()
        with self.assertRaises(WifiError):
            wifi.connect("Fibre-WPA3", PASSWORD)

    def test_weak_signal_and_no_dhcp_get_their_own_advice(self) -> None:
        _, wifi = self.start("weak-signal")
        with self.assertRaisesRegex(WifiError, "did not answer in time"):
            wifi.connect("Garden-Office", PASSWORD)
        _, wifi = self.start("no-dhcp")
        with self.assertRaisesRegex(WifiError, "did not give it an address"):
            wifi.connect("Locked-Down", PASSWORD)

    def test_diagnostics_show_the_emulated_log_and_router_flags(self) -> None:
        _, wifi = self.start("wpa3-mixed")
        with self.assertRaises(WifiError):
            wifi.connect("BT-Hub", PASSWORD)
        text = "\n".join(wifi.diagnostics("BT-Hub")["lines"])
        self.assertIn("Raspberry Pi 3 Model B Rev 1.2 · kernel 6.18.39+rpt-rpi-v8", text)
        self.assertIn("RSN: pair_ccmp group_ccmp psk sae", text)
        self.assertIn("4way_handshake", text)
        self.assertIn("reason=WRONG_KEY", text)


if __name__ == "__main__":
    unittest.main()
