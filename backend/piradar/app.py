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
from piradar.providers import AircraftProvider, MockAircraftProvider


def build_provider(config: Config) -> AircraftProvider:
    if config.provider == "mock":
        return MockAircraftProvider(config.home_latitude, config.home_longitude)
    raise ValueError(f"unsupported provider: {config.provider}")


def build_handler(
    config: Config,
    provider: AircraftProvider,
    frontend_dir: Path,
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
                        "provider_healthy": provider.healthy(),
                        "version": __version__,
                    }
                )
                return
            if path == "/api/config":
                self._json(config.public_dict())
                return
            if path == "/api/aircraft":
                aircraft = [track.to_dict() for track in provider.aircraft()]
                self._json(
                    {
                        "generated_at": datetime.now(UTC).isoformat(),
                        "source": provider.name,
                        "aircraft": aircraft,
                    }
                )
                return
            if path.startswith("/api/"):
                self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                return
            self._static(path)

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
            self.end_headers()
            self.wfile.write(body)

    return PiRadarHandler


def create_server(
    config: Config,
    provider: AircraftProvider | None = None,
    frontend_dir: Path | None = None,
) -> ThreadingHTTPServer:
    configured_frontend = os.getenv("PIRADAR_FRONTEND_DIR")
    resolved_frontend = frontend_dir or (
        Path(configured_frontend)
        if configured_frontend
        else Path(__file__).resolve().parents[2] / "frontend"
    )
    handler = build_handler(config, provider or build_provider(config), resolved_frontend)
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
