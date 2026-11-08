from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "scripts" / "lib" / "bootline.sh"
# The Pi's real boot line, including the ';' Raspberry Pi Imager adds.
CMDLINE = (
    "console=serial0,115200 console=tty1 root=PARTUUID=7bac7b86-02 rootfstype=ext4 "
    "fsck.repair=yes rootwait quiet splash plymouth.ignore-serial-consoles "
    "ds=nocloud;i=rpi-imager-1785669459115 cfg80211.ieee80211_regdom=GB"
)


class BootLineTests(unittest.TestCase):
    """Runs the shared shell helpers against a temporary boot directory."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.boot = Path(self.temporary.name)
        (self.boot / "cmdline.txt").write_text(CMDLINE + "\n")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def shell(self, script: str) -> str:
        environment = dict(os.environ, PIRADAR_BOOT_DIR=str(self.boot))
        result = subprocess.run(
            ["sh", "-eu", "-c", f". '{LIB}'; {script}"],
            env=environment, capture_output=True, text=True, check=True,
        )
        return result.stdout

    def cmdline(self) -> str:
        return (self.boot / "cmdline.txt").read_text()

    def test_add_reports_only_new_options_and_keeps_one_line(self) -> None:
        added = self.shell("cmdline_add quiet logo.nologo brcmfmac.feature_disable=0x82000")
        self.assertEqual(added.split(), ["logo.nologo", "brcmfmac.feature_disable=0x82000"])
        self.assertEqual(self.cmdline().count("\n"), 1)
        self.assertTrue(self.cmdline().startswith(CMDLINE + " "))
        self.assertTrue((self.boot / "cmdline.txt.piradar-bak").exists())

    def test_remove_takes_out_only_the_named_options(self) -> None:
        self.shell("cmdline_add logo.nologo brcmfmac.feature_disable=0x82000 >/dev/null")
        self.shell("cmdline_remove logo.nologo")
        self.assertEqual(self.cmdline(), CMDLINE + " brcmfmac.feature_disable=0x82000\n")
        self.shell("cmdline_remove brcmfmac.feature_disable=0x82000")
        self.assertEqual(self.cmdline(), CMDLINE + "\n")

    def test_options_are_never_expanded_as_file_globs(self) -> None:
        (self.boot / "cmdline.txt").write_text("root=/dev/sda* quiet\n")
        self.shell("cmdline_remove quiet")
        self.assertEqual(self.cmdline(), "root=/dev/sda*\n")


class WifiCompatScriptTests(unittest.TestCase):
    def test_script_uses_the_known_fix_and_shared_helpers(self) -> None:
        script = (ROOT / "scripts" / "wifi-compat.sh").read_text()
        self.assertIn("brcmfmac.feature_disable=0x82000", script)
        self.assertIn("lib/bootline.sh", script)
        self.assertIn("wifi-compat.sh", (ROOT / "scripts" / "install.sh").read_text())


if __name__ == "__main__":
    unittest.main()
