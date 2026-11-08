from __future__ import annotations

from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import threading
from typing import Any, Type
from urllib.parse import parse_qs, unquote, urlparse

from piradar import __version__
from piradar.config import Config
from piradar.location import PostcodeGeocoder
from piradar.providers import AdsbLolProvider, AircraftProvider, MockAircraftProvider
from piradar.storage import CredentialsStore, EnrichmentCache, LocationStore
from piradar.power import PowerError, SystemPower
from piradar.updates import UpdateError, UpdateManager
from piradar.wifi import NetworkManagerWifi, WifiError


def build_provider(
    config: Config,
    latitude: float | None = None,
    longitude: float | None = None,
) -> AircraftProvider:
    centre_latitude = config.home_latitude if latitude is None else latitude
    centre_longitude = config.home_longitude if longitude is None else longitude
    if config.provider == "mock":
        return MockAircraftProvider(centre_latitude, centre_longitude)
    if config.provider == "adsb_lol":
        cache = EnrichmentCache(Path(config.state_dir) / "enrichment.sqlite3")
        return AdsbLolProvider(
            centre_latitude,
            centre_longitude,
            config.range_nm,
            config.refresh_seconds,
            cache=cache,
        )
    raise ValueError(f"unsupported provider: {config.provider}")


class RadarRuntime:
    def __init__(
        self,
        config: Config,
        location_store: LocationStore,
        provider: AircraftProvider | None = None,
    ) -> None:
        self.config = config
        self.location_store = location_store
        self._lock = threading.RLock()
        self._location = location_store.load() or {
            "postcode": "",
            "latitude": config.home_latitude,
            "longitude": config.home_longitude,
        }
        self._provider = provider or build_provider(
            config,
            self._location["latitude"],
            self._location["longitude"],
        )

    @property
    def provider(self) -> AircraftProvider:
        with self._lock:
            return self._provider

    def public_config(self) -> dict[str, Any]:
        with self._lock:
            payload = self.config.public_dict()
            payload["home_latitude"] = self._location["latitude"]
            payload["home_longitude"] = self._location["longitude"]
            payload["postcode"] = self._location["postcode"]
            return payload

    def location(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._location)

    def replace_location(self, location: dict[str, Any]) -> dict[str, Any]:
        replacement = build_provider(
            self.config,
            float(location["latitude"]),
            float(location["longitude"]),
        )
        stored = self.location_store.replace(location)
        with self._lock:
            self._location = stored
            self._provider = replacement
            return dict(self._location)


def build_handler(
    config: Config,
    runtime: RadarRuntime,
    frontend_dir: Path,
    credentials_store: CredentialsStore,
    postcode_geocoder: PostcodeGeocoder,
    wifi_manager: NetworkManagerWifi,
    power: SystemPower,
    updates: UpdateManager,
) -> Type[BaseHTTPRequestHandler]:
    class PiRadarHandler(BaseHTTPRequestHandler):
        server_version = f"PiRadar/{__version__}"

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            path = urlparse(self.path).path
            if path == "/api/health":
                provider = runtime.provider
                self._json(
                    {
                        "status": "ok" if provider.healthy() else "degraded",
                        "provider": provider.name,
                        "provider_status": provider.status,
                        "provider_healthy": provider.healthy(),
                        "version": __version__,
                    }
                )
                return
            if path == "/api/config":
                self._json(runtime.public_config())
                return
            if path == "/api/settings/location":
                self._json({"location": runtime.location()})
                return
            if path == "/api/settings/services":
                self._json({"services": credentials_store.summary()})
                return
            if path == "/api/settings/wifi/diagnostics":
                # Shows log lines from the Pi, so only to its own screen.
                if self.client_address[0] not in {"127.0.0.1", "::1"}:
                    self._json({"error": "diagnostics are only available on the device"}, HTTPStatus.FORBIDDEN)
                    return
                ssid = (parse_qs(urlparse(self.path).query).get("ssid") or [None])[0]
                self._json({"diagnostics": wifi_manager.diagnostics(ssid)})
                return
            if path == "/api/settings/wifi":
                try:
                    networks = wifi_manager.scan()
                except WifiError as error:
                    self._json({"error": str(error)}, HTTPStatus.SERVICE_UNAVAILABLE)
                    return
                self._json({"networks": networks})
                return
            if path == "/api/system/update":
                # Local files only; never calls GitHub, so it is cheap to poll.
                self._json({"update": updates.status()})
                return
            if path == "/api/aircraft":
                provider = runtime.provider
                aircraft = [track.to_dict() for track in provider.aircraft()]
                self._json(
                    {
                        "generated_at": datetime.now(UTC).isoformat(),
                        "source": provider.name,
                        "status": provider.status,
                        "aircraft": aircraft,
                    }
                )
                return
            if path.startswith("/api/aircraft/"):
                provider = runtime.provider
                hex_code = unquote(path.removeprefix("/api/aircraft/")).strip().upper()
                if len(hex_code) != 6 or any(character not in "0123456789ABCDEF" for character in hex_code):
                    self._json({"error": "invalid aircraft identifier"}, HTTPStatus.BAD_REQUEST)
                    return
                details = provider.details(hex_code)
                if details is None:
                    self._json({"error": "aircraft not found"}, HTTPStatus.NOT_FOUND)
                    return
                self._json(details)
                return
            if path.startswith("/api/"):
                self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                return
            self._static(path)

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
            path = urlparse(self.path).path
            if path == "/api/settings/location":
                try:
                    payload = self._read_json()
                    postcode = payload.get("postcode")
                    if not isinstance(postcode, str):
                        raise ValueError("postcode is required")
                    location = runtime.replace_location(postcode_geocoder.lookup(postcode))
                except ValueError as error:
                    self._json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
                    return
                self._json(
                    {
                        "location": location,
                        "config": runtime.public_config(),
                    }
                )
                return
            if path == "/api/settings/wifi":
                try:
                    payload = self._read_json()
                    ssid = payload.get("ssid")
                    password = payload.get("password", "")
                    if not isinstance(ssid, str) or not isinstance(password, str):
                        raise WifiError("Select a network and enter its password.")
                    connection = wifi_manager.connect(ssid, password)
                except (ValueError, WifiError) as error:
                    response: dict[str, Any] = {"error": str(error)}
                    if getattr(error, "detail", None):
                        response["detail"] = error.detail
                    self._json(response, HTTPStatus.BAD_REQUEST)
                    return
                self._json({"connection": connection})
                return
            if path == "/api/system/update":
                if self.client_address[0] not in {"127.0.0.1", "::1"}:
                    self._json({"error": "updates can only be managed on the device"}, HTTPStatus.FORBIDDEN)
                    return
                try:
                    payload = self._read_json()
                    action = payload.get("action")
                    if action == "check":
                        result = updates.check(force=bool(payload.get("force")))
                    elif action == "install":
                        result = updates.install()
                    elif action == "auto" and isinstance(payload.get("enabled"), bool):
                        result = updates.set_auto(payload["enabled"])
                    else:
                        raise UpdateError("Choose check, install or auto.")
                except (ValueError, UpdateError) as error:
                    self._json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
                    return
                self._json({"update": result})
                return
            if path == "/api/system/power":
                # Shutdown/restart is only honoured from the Pi itself. The
                # server binds to loopback by default; this guards the case
                # where someone points PIRADAR_HOST at the network.
                if self.client_address[0] not in {"127.0.0.1", "::1"}:
                    self._json({"error": "power control is only available on the device"}, HTTPStatus.FORBIDDEN)
                    return
                try:
                    payload = self._read_json()
                    action = payload.get("action")
                    if not isinstance(action, str):
                        raise PowerError("Choose shut down or restart.")
                    result = power.request(action)
                except (ValueError, PowerError) as error:
                    self._json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
                    return
                self._json({"power": result})
                return
            if path != "/api/settings/services":
                self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                return
            try:
                payload = self._read_json()
                service = payload.get("service")
                credentials = payload.get("credentials")
                if not isinstance(service, str) or not isinstance(credentials, dict):
                    raise ValueError("service and credentials are required")
                services = credentials_store.replace(service, credentials)
            except ValueError as error:
                self._json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._json({"services": services})

        def log_message(self, format: str, *args: Any) -> None:
            print(f"{self.address_string()} - {format % args}")

        def _json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as error:
                raise ValueError("invalid content length") from error
            if length <= 0 or length > 16_384:
                raise ValueError("request body must be between 1 and 16384 bytes")
            try:
                payload = json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, UnicodeDecodeError) as error:
                raise ValueError("invalid JSON") from error
            if not isinstance(payload, dict):
                raise ValueError("JSON body must be an object")
            return payload

        def _static(self, request_path: str) -> None:
            relative = "index.html" if request_path == "/" else unquote(request_path.lstrip("/"))
            candidate = (frontend_dir / relative).resolve()
            try:
                candidate.relative_to(frontend_dir.resolve())
            except ValueError:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            if not candidate.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            body = candidate.read_bytes()
            content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8" if content_type.startswith("text/") else content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            if candidate.suffix in {".html", ".js", ".css"}:
                self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)

    return PiRadarHandler


def create_server(
    config: Config,
    provider: AircraftProvider | None = None,
    frontend_dir: Path | None = None,
    credentials_store: CredentialsStore | None = None,
    location_store: LocationStore | None = None,
    postcode_geocoder: PostcodeGeocoder | None = None,
    wifi_manager: NetworkManagerWifi | None = None,
    power: SystemPower | None = None,
    updates: UpdateManager | None = None,
) -> ThreadingHTTPServer:
    configured_frontend = os.getenv("PIRADAR_FRONTEND_DIR")
    resolved_frontend = frontend_dir or (
        Path(configured_frontend)
        if configured_frontend
        else Path(__file__).resolve().parents[2] / "frontend"
    )
    resolved_credentials = credentials_store or CredentialsStore(Path(config.state_dir) / "credentials.json")
    resolved_location = location_store or LocationStore(Path(config.state_dir) / "location.json")
    runtime = RadarRuntime(config, resolved_location, provider)
    handler = build_handler(
        config,
        runtime,
        resolved_frontend,
        resolved_credentials,
        postcode_geocoder or PostcodeGeocoder(),
        wifi_manager or NetworkManagerWifi(),
        power or SystemPower(),
        updates or UpdateManager(config.state_dir),
    )
    return ThreadingHTTPServer((config.host, config.port), handler)


def run(config: Config) -> None:
    server = create_server(config)
    print(f"PiRadar listening on http://{config.host}:{server.server_port} using {config.provider}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nPiRadar stopping")
    finally:
        server.server_close()
