from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

TargetLevel = Literal["beginner", "intermediate", "advanced"]
TeachingStyle = Literal["concise", "guided", "reference"]
BlueprintItemKind = Literal["module", "lesson"]
BlueprintDecision = Literal["approve", "reject"]

type JsonPrimitive = str | int | bool | None
type JsonValue = JsonPrimitive | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class GenerationIntent:
    target_level: TargetLevel
    target_duration_minutes: int
    intended_audience: str
    teaching_style: TeachingStyle
    locale: Literal["en"]
    supersedes_run_id: UUID | None


@dataclass(frozen=True, slots=True)
class ApproveBlueprintCommand:
    expected_run_row_version: int
    blueprint_id: UUID
    blueprint_revision: int
    expected_blueprint_content_sha256: str


@dataclass(frozen=True, slots=True)
class RejectGenerationCommand:
    expected_run_row_version: int
    expected_review_content_sha256: str
    reason_code: Literal[
        "GENERATION_CONTENT_REJECTED",
        "GENERATION_SOURCE_ALIGNMENT_REJECTED",
    ]


@dataclass(frozen=True, slots=True)
class SourceElementInput:
    id: UUID
    position: int
    kind: Literal["heading", "paragraph"]
    text: str
    text_sha256: str


@dataclass(frozen=True, slots=True)
class SourceSectionInput:
    id: UUID
    position: int
    title: str
    content_sha256: str
    elements: tuple[SourceElementInput, ...]


@dataclass(frozen=True, slots=True)
class BlueprintItemDraft:
    id: UUID
    kind: BlueprintItemKind
    parent_id: UUID | None
    position: int
    title: str
    description: str
    source_section_id: UUID


@dataclass(frozen=True, slots=True)
class BlueprintDraft:
    id: UUID
    schema_version: Literal["course-blueprint.v1"]
    title: str
    description: str
    intended_audience: str
    prerequisites: tuple[str, ...]
    learning_outcomes: tuple[str, ...]
    items: tuple[BlueprintItemDraft, ...]
    projection: JsonObject
    content_sha256: str


@dataclass(frozen=True, slots=True)
class GeneratedLessonDraft:
    id: UUID
    schema_version: Literal["course-draft.v1"]
    blueprint_lesson_item_id: UUID
    source_section_id: UUID
    title: str
    document: JsonObject
    content_sha256: str


@dataclass(frozen=True, slots=True)
class GenerationRunRecord:
    id: UUID
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID
    ingestion_run_id: UUID
    supersedes_run_id: UUID | None
    status: str
    target_level: str
    target_duration_minutes: int
    intended_audience: str
    teaching_style: str
    locale: str
    adapter: str
    provider: str
    model: str
    input_manifest_sha256: str
    blueprint_content_sha256: str | None
    output_manifest_sha256: str | None
    attempt_count: int
    max_attempts: int
    checkpoint: str
    reason_code: str | None
    row_version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class GenerationReviewPackage:
    run: GenerationRunRecord
    blueprint: BlueprintDraft | None
    lessons: tuple[GeneratedLessonDraft, ...]


@dataclass(frozen=True, slots=True)
class GenerationWorkerResult:
    run: GenerationRunRecord
    claimed: bool
