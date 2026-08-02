from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from piradar.app import create_server
from piradar.config import Config
from piradar.storage import CredentialsStore


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary_directory = tempfile.TemporaryDirectory()
        config = Config(host="127.0.0.1", port=0)
        frontend = Path(__file__).resolve().parents[1] / "frontend"
        credentials_store = CredentialsStore(Path(cls.temporary_directory.name) / "credentials.json")
        cls.server = create_server(config, frontend_dir=frontend, credentials_store=credentials_store)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.temporary_directory.cleanup()

    def get_json(self, path: str) -> dict:
        with urlopen(self.base_url + path, timeout=2) as response:
            self.assertEqual(response.headers.get_content_type(), "application/json")
            return json.load(response)

    def post_json(self, path: str, payload: dict) -> dict:
        request = Request(
            self.base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
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
        self.assertIn("aircraft_type", snapshot["aircraft"][0])

    def test_aircraft_details(self) -> None:
        details = self.get_json("/api/aircraft/406A91")
        self.assertEqual(details["manufacturer"], "Airbus")
        self.assertEqual(details["route"]["origin"]["code"], "LHR")

    def test_serves_frontend(self) -> None:
        with urlopen(self.base_url + "/", timeout=2) as response:
            body = response.read().decode("utf-8")
        self.assertIn("<title>PiRadar</title>", body)
        self.assertIn('id="map"', body)
        self.assertIn('id="detail-distance"', body)
        self.assertIn('id="options-control"', body)
        self.assertIn('id="filter-control"', body)
        self.assertIn('id="detail-type"', body)
        self.assertIn('id="open-services"', body)

    def test_serves_local_airport_layer(self) -> None:
        with urlopen(self.base_url + "/data/airports-gb.json", timeout=2) as response:
            airports = json.load(response)
        self.assertTrue(any(airport["iata"] == "OXF" for airport in airports))

    def test_serves_vendored_map_runtime(self) -> None:
        with urlopen(self.base_url + "/vendor/leaflet/leaflet.js", timeout=2) as response:
            body = response.read().decode("utf-8")
        self.assertIn("1.9.4", body)

    def test_position_refresh_preserves_enriched_details(self) -> None:
        with urlopen(self.base_url + "/app.js", timeout=2) as response:
            body = response.read().decode("utf-8")
        self.assertIn("populateDetail(selected, true)", body)
        self.assertIn("function populateDetail(track, resetEnrichment = false)", body)

    def test_unknown_api_is_json_404(self) -> None:
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base_url + "/api/nope", timeout=2)
        self.assertEqual(error.exception.code, 404)
        self.assertEqual(error.exception.headers.get_content_type(), "application/json")

    def test_credentials_api_never_returns_secret(self) -> None:
        secret = "not-a-real-flightaware-key"
        payload = self.post_json(
            "/api/settings/services",
            {"service": "flightaware", "credentials": {"api_key": secret}},
        )
        self.assertTrue(payload["services"]["flightaware"]["configured"])
        self.assertNotIn(secret, json.dumps(payload))

        status = self.get_json("/api/settings/services")
        self.assertTrue(status["services"]["flightaware"]["configured"])
        self.assertNotIn(secret, json.dumps(status))

        cleared = self.post_json(
            "/api/settings/services",
            {"service": "flightaware", "credentials": {"api_key": ""}},
        )
        self.assertFalse(cleared["services"]["flightaware"]["configured"])

    def test_credentials_api_rejects_unknown_fields(self) -> None:
        request = Request(
            self.base_url + "/api/settings/services",
            data=json.dumps({"service": "flightaware", "credentials": {"password": "nope"}}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as error:
            urlopen(request, timeout=2)
        self.assertEqual(error.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
