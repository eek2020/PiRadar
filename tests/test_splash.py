from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / "boot" / "plymouth" / "piradar"


class SplashThemeTests(unittest.TestCase):
    def test_every_image_the_script_loads_is_shipped(self) -> None:
        script = (THEME / "piradar.script").read_text()
        for name in re.findall(r'Image\("([^"+]+\.png)"\)', script):
            self.assertTrue((THEME / name).is_file(), f"missing {name}")
        frames = sorted(THEME.glob("sweep-*.png"))
        count = int(re.search(r"frame_count = (\d+);", script).group(1))
        self.assertEqual(len(frames), count)
        self.assertEqual(frames[0].name, "sweep-00.png")

    def test_theme_file_points_at_installed_location(self) -> None:
        theme = (THEME / "piradar.plymouth").read_text()
        self.assertIn("ModuleName=script", theme)
        self.assertIn("ScriptFile=/usr/share/plymouth/themes/piradar/piradar.script", theme)

    def test_installer_ships_theme_and_splash_script(self) -> None:
        install = (ROOT / "scripts" / "install.sh").read_text()
        self.assertIn('"$source_dir/boot"', install)
        self.assertIn("install-splash.sh", install)
        splash = (ROOT / "scripts" / "install-splash.sh").read_text()
        # Boot files are always backed up and the cmdline is kept to one line.
        self.assertIn("piradar-bak", splash)
        self.assertIn("head -n 1", splash)


if __name__ == "__main__":
    unittest.main()
