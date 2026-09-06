from __future__ import annotations

import hashlib
import json
import uuid
from uuid import UUID

from lms.modules.courses.validation import validate_rich_text_document

from .types import (
    BlueprintDraft,
    BlueprintItemDraft,
    GeneratedLessonDraft,
    GenerationIntent,
    JsonObject,
    JsonValue,
    SourceSectionInput,
)

ADAPTER_VERSION = "deterministic-source-course-v1"
BLUEPRINT_SCHEMA_VERSION = "course-blueprint.v1"
COURSE_DRAFT_SCHEMA_VERSION = "course-draft.v1"
GENERATION_POLICY_VERSION = "local-generation-policy-v1"
PROMPT_TEMPLATE_SHA256 = "sha256:8b403214afb4770c2999f5445a9a68c459d98611b2f82adfc531d52e4a540d24"


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        default=str,
    ).encode("utf-8")


def _sha256(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(value)).hexdigest()}"


def _stable_id(*parts: object) -> UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, "ai-lms:" + ":".join(str(part) for part in parts))


def _text_node(text: str) -> JsonObject:
    return {"type": "text", "text": text, "marks": []}


def _paragraph(text: str) -> JsonObject:
    return {"type": "paragraph", "content": [_text_node(text)]}


def _heading(text: str) -> JsonObject:
    return {"type": "heading", "level": 2, "content": [_text_node(text)]}


class DeterministicSourceCourseAdapter:
    """Local test adapter that performs no network or model invocation."""

    name = ADAPTER_VERSION
    provider = "local_deterministic"
    model = "none"

    def plan(
        self,
        *,
        run_id: UUID,
        source_title: str,
        intent: GenerationIntent,
        sections: tuple[SourceSectionInput, ...],
    ) -> BlueprintDraft:
        if not 1 <= len(sections) <= 100:
            raise ValueError("GENERATION_SOURCE_INVALID")
        if [section.position for section in sections] != list(range(1, len(sections) + 1)):
            raise ValueError("GENERATION_SOURCE_INVALID")
        title = source_title.strip()[:160]
        if not title:
            raise ValueError("GENERATION_SOURCE_INVALID")
        description = (
            f"A {intent.target_level} {intent.teaching_style} course for "
            f"{intent.intended_audience.strip()}."
        )[:2000]
        prerequisites = (
            ("No prior knowledge is required.",)
            if intent.target_level == "beginner"
            else ("Familiarity with the subject fundamentals is recommended.",)
        )
        outcomes = tuple(f"Explain {section.title.rstrip('.')}"[:300] for section in sections)
        items: list[BlueprintItemDraft] = []
        for section in sections:
            module_id = _stable_id("generation-blueprint-module", run_id, section.id)
            lesson_id = _stable_id("generation-blueprint-lesson", run_id, section.id)
            items.extend(
                (
                    BlueprintItemDraft(
                        id=module_id,
                        kind="module",
                        parent_id=None,
                        position=section.position,
                        title=section.title[:160],
                        description=f"Module derived from normalized section {section.position}.",
                        source_section_id=section.id,
                    ),
                    BlueprintItemDraft(
                        id=lesson_id,
                        kind="lesson",
                        parent_id=module_id,
                        position=1,
                        title=section.title[:160],
                        description=f"Lesson derived from normalized section {section.position}.",
                        source_section_id=section.id,
                    ),
                )
            )
        blueprint_id = _stable_id("generation-blueprint", run_id, 1)
        projection: JsonObject = {
            "schema_version": BLUEPRINT_SCHEMA_VERSION,
            "id": str(blueprint_id),
            "title": title,
            "description": description,
            "intended_audience": intent.intended_audience.strip(),
            "prerequisites": list(prerequisites),
            "learning_outcomes": list(outcomes),
            "items": [
                {
                    "id": str(item.id),
                    "kind": item.kind,
                    "parent_id": None if item.parent_id is None else str(item.parent_id),
                    "position": item.position,
                    "title": item.title,
                    "description": item.description,
                    "source_section_id": str(item.source_section_id),
                }
                for item in items
            ],
        }
        return BlueprintDraft(
            id=blueprint_id,
            schema_version="course-blueprint.v1",
            title=title,
            description=description,
            intended_audience=intent.intended_audience.strip(),
            prerequisites=prerequisites,
            learning_outcomes=outcomes,
            items=tuple(items),
            projection=projection,
            content_sha256=_sha256(projection),
        )

    def generate(
        self,
        *,
        run_id: UUID,
        blueprint: BlueprintDraft,
        sections: tuple[SourceSectionInput, ...],
    ) -> tuple[GeneratedLessonDraft, ...]:
        sections_by_id = {section.id: section for section in sections}
        lesson_items = tuple(item for item in blueprint.items if item.kind == "lesson")
        if not lesson_items or len(lesson_items) > 100:
            raise ValueError("GENERATION_OUTPUT_INVALID")
        lessons: list[GeneratedLessonDraft] = []
        for item in lesson_items:
            section = sections_by_id.get(item.source_section_id)
            if section is None or not section.elements:
                raise ValueError("GENERATION_SOURCE_EDGE_INVALID")
            nodes: list[JsonValue] = [_heading(item.title)]
            for element in section.elements:
                if not element.text.strip() or len(element.text) > 10_000:
                    raise ValueError("GENERATION_OUTPUT_INVALID")
                nodes.append(
                    _heading(element.text)
                    if element.kind == "heading"
                    else _paragraph(element.text)
                )
            document: JsonObject = {"type": "document", "content": nodes}
            validate_rich_text_document(document)
            lesson_id = _stable_id("generated-lesson-artifact", run_id, item.id, 1)
            projection: JsonObject = {
                "schema_version": COURSE_DRAFT_SCHEMA_VERSION,
                "id": str(lesson_id),
                "blueprint_lesson_item_id": str(item.id),
                "source_section_id": str(section.id),
                "title": item.title,
                "document": document,
            }
            lessons.append(
                GeneratedLessonDraft(
                    id=lesson_id,
                    schema_version="course-draft.v1",
                    blueprint_lesson_item_id=item.id,
                    source_section_id=section.id,
                    title=item.title,
                    document=document,
                    content_sha256=_sha256(projection),
                )
            )
        return tuple(lessons)
