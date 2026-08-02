from __future__ import annotations

from typing import Protocol

from piradar.models import Aircraft


class AircraftProvider(Protocol):
    name: str

    @property
    def status(self) -> str: ...

    def aircraft(self) -> list[Aircraft]: ...

    def healthy(self) -> bool: ...
