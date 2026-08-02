from __future__ import annotations

import json
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from piradar.app import create_server
from piradar.config import Config


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config = Config(host="127.0.0.1", port=0)
        frontend = Path(__file__).resolve().parents[1] / "frontend"
        cls.server = create_server(config, frontend_dir=frontend)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def get_json(self, path: str) -> dict:
        with urlopen(self.base_url + path, timeout=2) as response:
            self.assertEqual(response.headers.get_content_type(), "application/json")
            return json.load(response)

    def test_health(self) -> None:
        health = self.get_json("/api/health")
        self.assertEqual(health["status"], "ok")
        self.assertEqual(health["provider"], "mock")

    def test_aircraft_snapshot(self) -> None:
        snapshot = self.get_json("/api/aircraft")
        self.assertEqual(snapshot["source"], "mock")
        self.assertEqual(snapshot["status"], "live")
        self.assertGreater(len(snapshot["aircraft"]), 0)
        self.assertIn("callsign", snapshot["aircraft"][0])

    def test_serves_frontend(self) -> None:
        with urlopen(self.base_url + "/", timeout=2) as response:
            body = response.read().decode("utf-8")
        self.assertIn("<title>PiRadar</title>", body)
        self.assertIn('id="traffic-list"', body)
        self.assertIn('id="detail-distance"', body)

    def test_unknown_api_is_json_404(self) -> None:
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base_url + "/api/nope", timeout=2)
        self.assertEqual(error.exception.code, 404)
        self.assertEqual(error.exception.headers.get_content_type(), "application/json")


if __name__ == "__main__":
    unittest.main()
