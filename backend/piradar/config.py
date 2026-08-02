from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class Config:
    host: str = "127.0.0.1"
    port: int = 8080
    home_latitude: float = 51.5074
    home_longitude: float = -0.1278
    range_nm: int = 60
    provider: str = "mock"
    refresh_seconds: int = 8

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Config":
        values: dict[str, Any] = {}
        config_path = path or os.getenv("PIRADAR_CONFIG")
        if config_path:
            with Path(config_path).expanduser().open(encoding="utf-8") as handle:
                values.update(json.load(handle))

        environment = {
            "host": os.getenv("PIRADAR_HOST"),
            "port": os.getenv("PIRADAR_PORT"),
            "home_latitude": os.getenv("PIRADAR_HOME_LATITUDE"),
            "home_longitude": os.getenv("PIRADAR_HOME_LONGITUDE"),
            "range_nm": os.getenv("PIRADAR_RANGE_NM"),
            "provider": os.getenv("PIRADAR_PROVIDER"),
            "refresh_seconds": os.getenv("PIRADAR_REFRESH_SECONDS"),
        }
        values.update({key: value for key, value in environment.items() if value is not None})

        for key in ("port", "range_nm", "refresh_seconds"):
            if key in values:
                values[key] = int(values[key])
        for key in ("home_latitude", "home_longitude"):
            if key in values:
                values[key] = float(values[key])

        config = cls(**values)
        config.validate()
        return config

    def validate(self) -> None:
        if not 1 <= self.port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if not -90 <= self.home_latitude <= 90:
            raise ValueError("home_latitude must be between -90 and 90")
        if not -180 <= self.home_longitude <= 180:
            raise ValueError("home_longitude must be between -180 and 180")
        if not 1 <= self.range_nm <= 250:
            raise ValueError("range_nm must be between 1 and 250")
        if self.provider not in {"mock", "adsb_lol"}:
            raise ValueError(f"unsupported provider: {self.provider}")
        if not 2 <= self.refresh_seconds <= 60:
            raise ValueError("refresh_seconds must be between 2 and 60")

    def public_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in asdict(self).items()
            if key not in {"host", "port"}
        }
