from __future__ import annotations

import json
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from piradar.updates import UpdateError, UpdateManager

OLD_SHA = "a" * 40
NEW_SHA = "b" * 40


class FakeGitHub:
    """Returns a commit for any channel and records the URLs asked for."""

    def __init__(self, sha: str = NEW_SHA, fail: bool = False, direction: str = "ahead") -> None:
        self.sha = sha
        self.fail = fail
        self.direction = direction
        self.urls: list[str] = []

    def __call__(self, url: str) -> dict:
        self.urls.append(url)
        if self.fail:
            raise OSError("offline")
        if "/compare/" in url:
            return {"status": self.direction}
        return {"sha": self.sha, "commit": {"message": "Add things\n\nDetail", "committer": {"date": "2026-11-08T13:00:00Z"}}}


class RecordingRunner:
    def __init__(self, error: Exception | None = None) -> None:
        self.commands: list[list[str]] = []
        self.error = error

    def __call__(self, command, **kwargs):
        self.commands.append(command)
        if self.error:
            raise self.error
        return subprocess.CompletedProcess(command, 0, "", "")


class UpdateManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        (root / "opt").mkdir()
        (root / "opt" / "VERSION.json").write_text(json.dumps({"ref": "main", "sha": OLD_SHA}))
        self.channel_file = root / "update-channel"
        self.status_file = root / "status.json"
        self.github = FakeGitHub()
        self.runner = RecordingRunner()
        self.now = time.time()
        self.manager = UpdateManager(
            root / "state",
            install_dir=root / "opt",
            channel_file=self.channel_file,
            status_file=self.status_file,
            fetch=self.github,
            runner=self.runner,
            clock=lambda: self.now,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_status_without_network_reports_installed_version(self) -> None:
        status = self.manager.status()
        self.assertEqual(status["channel"], "main")
        self.assertEqual(status["installed"]["short"], "aaaaaaa")
        from piradar import __version__
        self.assertEqual(status["installed"]["version"], __version__)
        self.assertIsNone(status["available"])
        self.assertEqual(self.github.urls, [])

    def test_check_compares_latest_commit_on_the_channel(self) -> None:
        self.channel_file.write_text("fix/keyboard-case-and-symbols\n")
        status = self.manager.check()
        self.assertTrue(status["available"])
        self.assertEqual(status["latest"]["summary"], "Add things")
        self.assertTrue(self.github.urls[0].endswith("/commits/fix/keyboard-case-and-symbols"))

        self.assertTrue(self.github.urls[1].endswith(f"/compare/{OLD_SHA}...{NEW_SHA}"))

        self.github.sha = OLD_SHA
        self.assertTrue(self.manager.check()["available"], "cached answer should be reused")
        self.assertFalse(self.manager.check(force=True)["available"])
        self.assertEqual(len(self.github.urls), 3)

    def test_installed_commit_unknown_to_github_does_not_block_updates(self) -> None:
        def fetch(url: str) -> dict:
            if "/compare/" in url:
                raise OSError("404 Not Found")
            return {"sha": NEW_SHA, "commit": {"message": "x", "committer": {}}}
        self.manager._fetch = fetch
        self.assertTrue(self.manager.check()["available"])

    def test_an_older_channel_is_never_offered(self) -> None:
        # e.g. following main before the feature branch has been merged
        self.github.direction = "behind"
        status = self.manager.check()
        self.assertFalse(status["available"])
        self.assertEqual(status["latest"]["direction"], "behind")

    def test_check_offline_gives_a_clear_message(self) -> None:
        self.github.fail = True
        with self.assertRaisesRegex(UpdateError, "online"):
            self.manager.check()

    def test_install_starts_only_the_update_unit_without_blocking(self) -> None:
        self.manager.install()
        self.assertEqual(self.runner.commands, [["systemctl", "start", "--no-block", "piradar-update.service"]])

    def test_install_refused_while_an_update_runs_but_not_after_a_stale_run(self) -> None:
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.now - 60))
        self.status_file.write_text(json.dumps({"state": "testing", "at": stamp}))
        with self.assertRaisesRegex(UpdateError, "already running"):
            self.manager.install()
        old = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.now - 3600))
        self.status_file.write_text(json.dumps({"state": "testing", "at": old}))
        self.assertEqual(self.manager.progress()["state"], "interrupted")
        self.manager.install()

    def test_install_permission_problem_is_explained(self) -> None:
        self.manager._runner = RecordingRunner(subprocess.CalledProcessError(1, ["systemctl"]))
        with self.assertRaisesRegex(UpdateError, "update rule"):
            self.manager.install()

    def test_auto_switch_is_stored_where_the_nightly_updater_reads_it(self) -> None:
        self.assertFalse(self.manager.status()["auto"])
        self.manager.set_auto(True)
        stored = json.loads(self.manager.settings_file.read_text())
        self.assertEqual(stored, {"auto": True})
        self.assertTrue(self.manager.status()["auto"])
        self.assertEqual(self.manager.settings_file.stat().st_mode & 0o777, 0o644)


class UpdatePlumbingTests(unittest.TestCase):
    """The updater, units and permission rule must agree with each other."""

    def test_units_rule_and_installer_line_up(self) -> None:
        root = Path(__file__).resolve().parents[1]
        rule = (root / "polkit" / "50-piradar-update.rules").read_text()
        self.assertIn('action.lookup("unit") === "piradar-update.service"', rule)
        self.assertIn('action.lookup("verb") === "start"', rule)
        self.assertIn("--if-newer", (root / "systemd" / "piradar-update.service").read_text())
        self.assertIn("--auto", (root / "systemd" / "piradar-update-auto.service").read_text())
        self.assertIn("Unit=piradar-update-auto.service", (root / "systemd" / "piradar-update.timer").read_text())
        install = (root / "scripts" / "install.sh").read_text()
        for name in ("piradar-update.service", "piradar-update-auto.service", "piradar-update.timer", "50-piradar-update.rules"):
            self.assertIn(name, install)
        update = (root / "scripts" / "update.sh").read_text()
        self.assertIn("/var/lib/piradar/update-settings.json", update)
        self.assertIn("/var/lib/piradar-update/status.json", update)


if __name__ == "__main__":
    unittest.main()
