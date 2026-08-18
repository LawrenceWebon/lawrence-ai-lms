from __future__ import annotations

import hashlib
import json
from typing import cast

from .types import CourseSnapshot, JsonObject, JsonValue


def _require_f002_json_subset(value: object) -> None:
    if value is None or isinstance(value, str) or type(value) in {bool, int}:
        return
    if isinstance(value, list):
        for item in value:
            _require_f002_json_subset(item)
        return
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        for item in value.values():
            _require_f002_json_subset(item)
        return
    raise ValueError("Value is outside the canonical F-002 JSON subset.")


def canonical_json_bytes(value: object) -> bytes:
    """Serialize the F-002 JSON subset using RFC 8785 canonical form.

    F-002 admits only integers, booleans, strings, arrays, and objects with ASCII
    contract keys. For that subset, strict stdlib JSON serialization is the JCS form.
    Floating-point and non-JSON values are intentionally outside the contract.
    """

    _require_f002_json_subset(value)
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return encoded.encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise ValueError("Value is outside the canonical F-002 JSON subset.") from error


def content_projection(snapshot: CourseSnapshot) -> JsonObject:
    sections: list[JsonValue] = []
    for section in sorted(snapshot.sections, key=lambda item: item.position):
        lessons: list[JsonValue] = []
        for lesson in sorted(section.lessons, key=lambda item: item.position):
            blocks: list[JsonValue] = []
            for block in sorted(lesson.content_blocks, key=lambda item: item.position):
                blocks.append(
                    {
                        "kind": block.kind,
                        "position": block.position,
                        "document": cast(JsonValue, block.document),
                    }
                )
            lessons.append(
                {
                    "title": lesson.title,
                    "position": lesson.position,
                    "is_required": lesson.is_required,
                    "content_blocks": blocks,
                }
            )
        sections.append(
            {
                "title": section.title,
                "position": section.position,
                "lessons": lessons,
            }
        )
    return {
        "primary_locale": snapshot.version.primary_locale,
        "title": snapshot.version.title,
        "description": snapshot.version.description,
        "sections": sections,
    }


def canonical_content_hash(snapshot: CourseSnapshot) -> str:
    digest = hashlib.sha256(canonical_json_bytes(content_projection(snapshot))).hexdigest()
    return f"sha256:{digest}"


def canonical_request_hash(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()
