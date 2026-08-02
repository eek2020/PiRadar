from __future__ import annotations

from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
from typing import Any, Type
from urllib.parse import unquote, urlparse

from piradar import __version__
from piradar.config import Config
from piradar.providers import AdsbLolProvider, AircraftProvider, MockAircraftProvider
from piradar.storage import CredentialsStore, EnrichmentCache


def build_provider(config: Config) -> AircraftProvider:
    if config.provider == "mock":
        return MockAircraftProvider(config.home_latitude, config.home_longitude)
    if config.provider == "adsb_lol":
        cache = EnrichmentCache(Path(config.state_dir) / "enrichment.sqlite3")
        return AdsbLolProvider(
            config.home_latitude,
            config.home_longitude,
            config.range_nm,
            config.refresh_seconds,
            cache=cache,
        )
    raise ValueError(f"unsupported provider: {config.provider}")


def build_handler(
    config: Config,
    provider: AircraftProvider,
    frontend_dir: Path,
    credentials_store: CredentialsStore,
) -> Type[BaseHTTPRequestHandler]:
    class PiRadarHandler(BaseHTTPRequestHandler):
        server_version = f"PiRadar/{__version__}"

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            path = urlparse(self.path).path
            if path == "/api/health":
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
                self._json(config.public_dict())
                return
            if path == "/api/settings/services":
                self._json({"services": credentials_store.summary()})
                return
            if path == "/api/aircraft":
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
) -> ThreadingHTTPServer:
    configured_frontend = os.getenv("PIRADAR_FRONTEND_DIR")
    resolved_frontend = frontend_dir or (
        Path(configured_frontend)
        if configured_frontend
        else Path(__file__).resolve().parents[2] / "frontend"
    )
    resolved_credentials = credentials_store or CredentialsStore(Path(config.state_dir) / "credentials.json")
    handler = build_handler(config, provider or build_provider(config), resolved_frontend, resolved_credentials)
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
