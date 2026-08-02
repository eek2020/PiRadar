from __future__ import annotations

from typing import Any, Protocol

from piradar.models import Aircraft


class AircraftProvider(Protocol):
    name: str

    @property
    def status(self) -> str: ...

    def aircraft(self) -> list[Aircraft]: ...

    def healthy(self) -> bool: ...

    def details(self, hex_code: str) -> dict[str, Any] | None: ...
