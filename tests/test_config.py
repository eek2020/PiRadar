from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from piradar.config import Config


class ConfigTests(unittest.TestCase):
    def test_defaults_are_valid(self) -> None:
        config = Config.load()
        self.assertEqual(config.provider, "mock")
        self.assertEqual(config.range_nm, 60)

    def test_file_and_environment_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({"range_nm": 25, "port": 9000}), encoding="utf-8")
            with patch.dict(os.environ, {"PIRADAR_RANGE_NM": "40"}, clear=True):
                config = Config.load(path)
        self.assertEqual(config.range_nm, 40)
        self.assertEqual(config.port, 9000)

    def test_rejects_invalid_location(self) -> None:
        with self.assertRaisesRegex(ValueError, "home_latitude"):
            Config(home_latitude=91).validate()

    def test_public_config_does_not_expose_listener(self) -> None:
        public = Config(host="0.0.0.0", port=9999).public_dict()
        self.assertNotIn("host", public)
        self.assertNotIn("port", public)


if __name__ == "__main__":
    unittest.main()

