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
from piradar.storage import CredentialsStore, LocationStore
from piradar.updates import UpdateManager


class FakePostcodeGeocoder:
    def lookup(self, postcode: str) -> dict[str, object]:
        if postcode.replace(" ", "").upper() != "OX11AA":
            raise ValueError("postcode not found")
        return {"postcode": "OX1 1AA", "latitude": 51.752, "longitude": -1.2577}


class FakeWifiManager:
    def __init__(self) -> None:
        self.networks = [
            {"ssid": "Current Wi-Fi", "signal": 82, "security": "WPA2", "secured": True, "connected": True, "supported": True},
            {"ssid": "Guest", "signal": 55, "security": "Open", "secured": False, "connected": False, "supported": True},
        ]

    def scan(self) -> list[dict[str, object]]:
        return self.networks

    def connect(self, ssid: str, password: str) -> dict[str, object]:
        if ssid not in {network["ssid"] for network in self.networks}:
            raise ValueError("network not scanned")
        return {"ssid": ssid, "connected": True}

    def diagnostics(self, ssid: str | None = None) -> dict[str, object]:
        return {"lines": [f"Router: {ssid}", "Log (most recent last):"]}


class FakePower:
    """Records power requests instead of switching anything off."""

    def __init__(self) -> None:
        self.requests: list[str] = []

    def request(self, action: str) -> dict[str, object]:
        from piradar.power import PowerError

        if action not in {"poweroff", "reboot"}:
            raise PowerError("Choose shut down or restart.")
        self.requests.append(action)
        return {"action": action, "accepted": True}


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary_directory = tempfile.TemporaryDirectory()
        config = Config(host="127.0.0.1", port=0)
        frontend = Path(__file__).resolve().parents[1] / "frontend"
        credentials_store = CredentialsStore(Path(cls.temporary_directory.name) / "credentials.json")
        cls.location_store = LocationStore(Path(cls.temporary_directory.name) / "location.json")
        cls.wifi_manager = FakeWifiManager()
        cls.power = FakePower()
        update_root = Path(cls.temporary_directory.name)
        cls.update_commands: list[list[str]] = []
        cls.updates = UpdateManager(
            update_root / "state",
            install_dir=update_root,
            channel_file=update_root / "update-channel",
            status_file=update_root / "update-status.json",
            fetch=lambda url: {"status": "ahead"} if "/compare/" in url else {"sha": "c" * 40, "commit": {"message": "New build", "committer": {"date": "2026-11-08T13:00:00Z"}}},
            runner=lambda command, **kwargs: cls.update_commands.append(command),
        )
        cls.server = create_server(
            config,
            frontend_dir=frontend,
            credentials_store=credentials_store,
            location_store=cls.location_store,
            postcode_geocoder=FakePostcodeGeocoder(),
            wifi_manager=cls.wifi_manager,
            power=cls.power,
            updates=cls.updates,
        )
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
        self.assertIn('id="open-wifi"', body)
        self.assertIn('id="wifi-networks"', body)
        self.assertIn('id="wifi-password"', body)
        self.assertIn('id="airport-detail"', body)
        self.assertIn('id="location-postcode"', body)
        # Two keyboards: a postcode pad and a full keyboard for everything else.
        self.assertIn('id="postcode-keyboard"', body)
        self.assertIn('id="text-keyboard"', body)
        self.assertIn('id="location-postcode" data-osk="postcode"', body)
        self.assertIn('id="wifi-password" data-osk', body)
        # The keys themselves are built in app.js from layout data.
        with urlopen(self.base_url + "/app.js", timeout=2) as response:
            script = response.read().decode("utf-8")
        self.assertIn('action: "backspace"', script)
        self.assertIn('action: "submit"', script)
        self.assertIn('action: "caps"', script)
        self.assertIn('action: "shift"', script)

    def test_update_panel_values_cannot_push_rows_off_screen(self) -> None:
        # Regression: a long commit message once widened every row past 800px.
        with urlopen(self.base_url + "/styles.css", timeout=2) as response:
            body = response.read().decode("utf-8")
        self.assertIn("grid-template-columns: minmax(0, 1fr)", body)
        self.assertIn(".update-facts dd { flex: 1 1 auto; min-width: 0;", body)

    def test_kiosk_controls_are_touch_optimised_and_hide_the_cursor(self) -> None:
        with urlopen(self.base_url + "/styles.css", timeout=2) as response:
            body = response.read().decode("utf-8")
        self.assertIn("cursor: none !important", body)
        self.assertIn("button, label, input { touch-action: manipulation; }", body)
        self.assertIn("pointer-events: auto; touch-action: manipulation;", body)

    def test_bogus_hdmi_pointer_is_ignored_by_libinput(self) -> None:
        rule = Path(__file__).resolve().parents[1] / "udev" / "99-piradar-input.rules"
        body = rule.read_text(encoding="utf-8")
        self.assertIn('ATTRS{name}=="vc4-hdmi"', body)
        self.assertIn('ENV{LIBINPUT_IGNORE_DEVICE}="1"', body)

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

    def test_airports_are_selectable(self) -> None:
        with urlopen(self.base_url + "/app.js", timeout=2) as response:
            body = response.read().decode("utf-8")
        self.assertIn('function selectAirport(airport)', body)
        self.assertIn('.on("click", () => selectAirport(airport))', body)

    def test_kiosk_cannot_navigate_through_map_attribution(self) -> None:
        with urlopen(self.base_url + "/app.js", timeout=2) as response:
            javascript = response.read().decode("utf-8")
        with urlopen(self.base_url + "/styles.css", timeout=2) as response:
            stylesheet = response.read().decode("utf-8")
        self.assertIn('attribution: "© OpenStreetMap contributors"', javascript)
        self.assertIn('addAttribution("Airports: OurAirports")', javascript)
        self.assertNotIn('attribution: \'&copy; <a href=', javascript)
        self.assertIn('document.addEventListener("click", preventKioskNavigation, true)', javascript)
        self.assertIn('if (link.closest(".leaflet-control-zoom")) return;', javascript)
        self.assertIn("pointer-events: none !important", stylesheet)

    def test_unknown_api_is_json_404(self) -> None:
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base_url + "/api/nope", timeout=2)
        self.assertEqual(error.exception.code, 404)
        self.assertEqual(error.exception.headers.get_content_type(), "application/json")

    def test_postcode_updates_and_persists_radar_location(self) -> None:
        payload = self.post_json("/api/settings/location", {"postcode": "ox1 1aa"})
        self.assertEqual(payload["location"]["postcode"], "OX1 1AA")
        self.assertAlmostEqual(payload["config"]["home_latitude"], 51.752)
        self.assertEqual(self.get_json("/api/settings/location")["location"]["postcode"], "OX1 1AA")
        self.assertEqual(self.location_store.load()["postcode"], "OX1 1AA")

    def test_invalid_postcode_does_not_replace_location(self) -> None:
        before = self.get_json("/api/settings/location")["location"]
        with self.assertRaises(HTTPError) as error:
            self.post_json("/api/settings/location", {"postcode": "not a postcode"})
        self.assertEqual(error.exception.code, 400)
        self.assertEqual(self.get_json("/api/settings/location")["location"], before)

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

    def test_wifi_api_lists_scanned_networks_and_connects_selection(self) -> None:
        networks = self.get_json("/api/settings/wifi")["networks"]
        self.assertEqual(networks[0]["ssid"], "Current Wi-Fi")
        self.assertNotIn("password", json.dumps(networks))

        connected = self.post_json("/api/settings/wifi", {"ssid": "Guest", "password": ""})
        self.assertEqual(connected["connection"], {"ssid": "Guest", "connected": True})


    def test_power_api_accepts_only_shutdown_and_restart(self) -> None:
        result = self.post_json("/api/system/power", {"action": "poweroff"})
        self.assertEqual(result["power"], {"action": "poweroff", "accepted": True})
        self.assertEqual(self.power.requests[-1], "poweroff")

        request = Request(
            self.base_url + "/api/system/power",
            data=json.dumps({"action": "halt; rm -rf /"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=2)
        self.assertEqual(raised.exception.code, 400)
        self.assertEqual(self.power.requests, ["poweroff"])

    def test_frontend_has_password_reveal_and_power_controls(self) -> None:
        with urlopen(self.base_url + "/", timeout=2) as response:
            body = response.read().decode("utf-8")
        self.assertEqual(body.count("data-reveal"), body.count('type="password"'))
        self.assertIn('id="open-power"', body)
        self.assertIn('data-power="poweroff"', body)
        self.assertIn('data-power="reboot"', body)
        self.assertIn('id="open-updates"', body)
        self.assertIn('id="update-install"', body)


    def test_update_api_reports_checks_installs_and_stores_auto(self) -> None:
        status = self.get_json("/api/system/update")["update"]
        self.assertEqual(status["channel"], "main")
        self.assertIsNone(status["available"])

        checked = self.post_json("/api/system/update", {"action": "check"})["update"]
        self.assertTrue(checked["available"])
        self.assertEqual(checked["latest"]["summary"], "New build")

        self.post_json("/api/system/update", {"action": "install"})
        self.assertEqual(self.update_commands[-1], ["systemctl", "start", "--no-block", "piradar-update.service"])

        self.assertTrue(self.post_json("/api/system/update", {"action": "auto", "enabled": True})["update"]["auto"])

        request = Request(
            self.base_url + "/api/system/update",
            data=json.dumps({"action": "uninstall"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=2)
        self.assertEqual(raised.exception.code, 400)


    def test_wifi_diagnostics_endpoint_passes_the_network_name(self) -> None:
        result = self.get_json("/api/settings/wifi/diagnostics?ssid=Home%20Hub")
        self.assertEqual(result["diagnostics"]["lines"][0], "Router: Home Hub")


if __name__ == "__main__":
    unittest.main()
