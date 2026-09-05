from __future__ import annotations

import io
import json
import math
import os
import resource
import socket
import sys
from typing import Never

_CPU_LIMIT_SECONDS = 15
_ADDRESS_SPACE_LIMIT_BYTES = 192 * 1024 * 1024
_ROOT_OBJECT_RECOVERY_LIMIT = 10_000


def _network_disabled(*_args: object, **_kwargs: object) -> Never:
    raise OSError("network access is disabled for PDF inspection")


def _apply_process_boundary() -> None:
    os.environ.clear()
    socket.socket = _network_disabled  # type: ignore[assignment, misc]
    resource.setrlimit(
        resource.RLIMIT_CPU,
        (_CPU_LIMIT_SECONDS, _CPU_LIMIT_SECONDS),
    )
    resource.setrlimit(
        resource.RLIMIT_AS,
        (_ADDRESS_SPACE_LIMIT_BYTES, _ADDRESS_SPACE_LIMIT_BYTES),
    )


def _emit(outcome: str, *, page_boxes: list[list[float]] | None = None) -> int:
    observation: dict[str, object] = {"outcome": outcome}
    if page_boxes is not None:
        observation["page_boxes"] = page_boxes
    sys.stdout.write(json.dumps(observation, separators=(",", ":")))
    return 0


def main() -> int:
    _apply_process_boundary()

    from pypdf import PdfReader
    from pypdf.errors import PyPdfError

    body = sys.stdin.buffer.read()
    try:
        reader = PdfReader(
            io.BytesIO(body),
            strict=True,
            root_object_recovery_limit=_ROOT_OBJECT_RECOVERY_LIMIT,
        )
        if reader.is_encrypted:
            return _emit("encrypted")
        root = reader.root_object
        if root.get("/Type") != "/Catalog":
            return _emit("corrupt")

        page_boxes: list[list[float]] = []
        for page in reader.pages:
            box = page.mediabox
            coordinates = [
                float(box.left),
                float(box.bottom),
                float(box.right),
                float(box.top),
            ]
            if not all(math.isfinite(value) for value in coordinates):
                return _emit("corrupt")
            if coordinates[2] <= coordinates[0] or coordinates[3] <= coordinates[1]:
                return _emit("corrupt")
            page_boxes.append(coordinates)
        if not page_boxes:
            return _emit("corrupt")
    except EOFError, KeyError, OSError, PyPdfError, RecursionError, TypeError, ValueError:
        return _emit("corrupt")

    return _emit("accepted", page_boxes=page_boxes)


if __name__ == "__main__":
    raise SystemExit(main())
