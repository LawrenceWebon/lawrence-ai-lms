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
_MAX_EXTRACTED_TEXT_BYTES = 64 * 1024 * 1024


def _network_disabled(*_args: object, **_kwargs: object) -> Never:
    raise OSError("network access is disabled for PDF extraction")


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


def _emit(outcome: str, *, pages: list[dict[str, object]] | None = None) -> int:
    observation: dict[str, object] = {"outcome": outcome}
    if pages is not None:
        observation["pages"] = pages
    sys.stdout.write(json.dumps(observation, ensure_ascii=False, separators=(",", ":")))
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
        if reader.root_object.get("/Type") != "/Catalog":
            return _emit("failed")

        pages: list[dict[str, object]] = []
        extracted_bytes = 0
        for page_number, page in enumerate(reader.pages, start=1):
            box = page.mediabox
            coordinates = [
                float(box.left),
                float(box.bottom),
                float(box.right),
                float(box.top),
            ]
            if not all(math.isfinite(value) for value in coordinates):
                return _emit("failed")
            width = coordinates[2] - coordinates[0]
            height = coordinates[3] - coordinates[1]
            if width <= 0 or height <= 0:
                return _emit("failed")
            contents = page.get_contents()
            text = (
                ""
                if contents is None
                else page.extract_text(
                    extraction_mode="layout",
                    layout_mode_space_vertically=False,
                )
            )
            if not isinstance(text, str):
                return _emit("failed")
            extracted_bytes += len(text.encode("utf-8"))
            if extracted_bytes > _MAX_EXTRACTED_TEXT_BYTES:
                return _emit("too_large")
            pages.append(
                {
                    "number": page_number,
                    "width_points": width,
                    "height_points": height,
                    "text": text,
                }
            )
        if not pages:
            return _emit("failed")
    except EOFError, KeyError, OSError, PyPdfError, RecursionError, TypeError, ValueError:
        return _emit("failed")

    return _emit("extracted", pages=pages)


if __name__ == "__main__":
    raise SystemExit(main())
