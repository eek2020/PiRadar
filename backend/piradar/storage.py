from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
from typing import Any, Callable


SERVICE_FIELDS: dict[str, tuple[str, ...]] = {
    "flightaware": ("api_key",),
    "flightradar24": ("api_token",),
    "amadeus": ("client_id", "client_secret"),
}


class EnrichmentCache:
    def __init__(self, path: str | Path, *, clock: Callable[[], float] = time.time) -> None:
        self.path = Path(path)
        self._clock = clock

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS enrichment_cache (
                namespace TEXT NOT NULL,
                cache_key TEXT NOT NULL,
                payload TEXT NOT NULL,
                fetched_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                PRIMARY KEY (namespace, cache_key)
            )
            """
        )
        os.chmod(self.path, 0o600)
        return connection

    def get(self, namespace: str, cache_key: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload, expires_at FROM enrichment_cache WHERE namespace = ? AND cache_key = ?",
                (namespace, cache_key),
            ).fetchone()
            if row is None:
                return None
            if int(row[1]) <= int(self._clock()):
                connection.execute(
                    "DELETE FROM enrichment_cache WHERE namespace = ? AND cache_key = ?",
                    (namespace, cache_key),
                )
                return None
            return json.loads(row[0])

    def set(self, namespace: str, cache_key: str, payload: dict[str, Any], ttl_seconds: int) -> None:
        fetched_at = int(self._clock())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO enrichment_cache(namespace, cache_key, payload, fetched_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(namespace, cache_key) DO UPDATE SET
                    payload = excluded.payload,
                    fetched_at = excluded.fetched_at,
                    expires_at = excluded.expires_at
                """,
                (
                    namespace,
                    cache_key,
                    json.dumps(payload, separators=(",", ":")),
                    fetched_at,
                    fetched_at + ttl_seconds,
                ),
            )

    def purge_expired(self) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM enrichment_cache WHERE expires_at <= ?",
                (int(self._clock()),),
            )
            return cursor.rowcount


class CredentialsStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()

    def _load(self) -> dict[str, dict[str, str]]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        if not isinstance(payload, dict):
            return {}
        return {
            service: {field: str(value) for field, value in values.items() if field in SERVICE_FIELDS.get(service, ())}
            for service, values in payload.items()
            if isinstance(values, dict) and service in SERVICE_FIELDS
        }

    def summary(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            stored = self._load()
            return {
                service: {
                    "configured": all(bool(stored.get(service, {}).get(field)) for field in fields),
                    "fields": list(fields),
                }
                for service, fields in SERVICE_FIELDS.items()
            }

    def replace(self, service: str, credentials: dict[str, Any]) -> dict[str, dict[str, Any]]:
        if service not in SERVICE_FIELDS:
            raise ValueError("unsupported data service")
        expected = SERVICE_FIELDS[service]
        if any(field not in expected for field in credentials):
            raise ValueError("unsupported credential field")

        with self._lock:
            stored = self._load()
            values = {field: str(credentials.get(field, "")).strip() for field in expected}
            if any(values.values()) and not all(values.values()):
                raise ValueError("all credential fields are required")
            if all(values.values()):
                stored[service] = values
            else:
                stored.pop(service, None)
            self._write(stored)
            return self.summary()

    def credentials(self, service: str) -> dict[str, str]:
        if service not in SERVICE_FIELDS:
            return {}
        with self._lock:
            return dict(self._load().get(service, {}))

    def _write(self, payload: dict[str, dict[str, str]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_path = tempfile.mkstemp(prefix="credentials-", dir=self.path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, separators=(",", ":"))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary_path, 0o600)
            os.replace(temporary_path, self.path)
        finally:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
