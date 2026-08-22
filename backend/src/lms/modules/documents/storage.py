from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

_LOCATOR_PATTERN = re.compile(r"^[0-9a-f]{32}\.pdf$")


@dataclass(frozen=True, slots=True)
class StoredObjectObservation:
    locator: str
    byte_count: int


class LocalQuarantineStorage:
    """Private local adapter used only for synthetic/right-cleared F-003 fixtures."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def _path(self, locator: str) -> Path:
        if _LOCATOR_PATTERN.fullmatch(locator) is None:
            raise ValueError("invalid private quarantine locator")
        return self._root / locator

    @staticmethod
    def locator_for(intent_id: UUID) -> str:
        return f"{intent_id.hex}.pdf"

    def put(self, *, intent_id: UUID, body: bytes) -> StoredObjectObservation:
        self._root.mkdir(mode=0o700, parents=True, exist_ok=True)
        locator = self.locator_for(intent_id)
        destination = self._path(locator)
        temporary = self._root / f".{intent_id.hex}.upload"
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        return StoredObjectObservation(locator=locator, byte_count=len(body))

    def read(self, locator: str) -> bytes:
        return self._path(locator).read_bytes()

    def delete(self, locator: str) -> None:
        self._path(locator).unlink(missing_ok=True)

    def exists(self, locator: str) -> bool:
        return self._path(locator).is_file()

    def locators(self) -> tuple[str, ...]:
        if not self._root.exists():
            return ()
        return tuple(
            sorted(
                child.name
                for child in self._root.iterdir()
                if child.is_file() and _LOCATOR_PATTERN.fullmatch(child.name)
            )
        )
