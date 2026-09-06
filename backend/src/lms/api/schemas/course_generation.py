from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Annotated, Literal, Protocol, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Sha256 = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
GenerationStatus = Literal[
    "queued",
    "planning",
    "blueprint_review",
    "generation_queued",
    "generating",
    "review_ready",
    "canonicalized",
    "rejected",
    "retryable",
    "failed",
    "rights_blocked",
]
GenerationRejectionReason = Literal[
    "GENERATION_CONTENT_REJECTED",
    "GENERATION_SOURCE_ALIGNMENT_REJECTED",
]


def _require_timezone(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return value


class GenerationContractError(Exception):
    def __init__(
        self,
        *,
        code: str,
        errors: Sequence[dict[str, object]] = (),
    ) -> None:
        super().__init__(code)
        self.code = code
        self.errors = tuple(errors)


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class StartCourseGenerationV1(StrictSchema):
    source_document_id: UUID
    source_version_id: UUID
    ingestion_run_id: UUID
    target_level: Literal["beginner", "intermediate", "advanced"]
    target_duration_minutes: int = Field(ge=1, le=10_000, strict=True)
    intended_audience: Annotated[str, Field(min_length=1, max_length=300)]
    teaching_style: Literal["concise", "guided", "reference"]
    locale: Literal["en"] = "en"
    supersedes_run_id: UUID | None = None

    @field_validator("intended_audience")
    @classmethod
    def require_trimmed_audience(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("intended audience must be trimmed")
        return value


class ApproveGenerationBlueprintV1(StrictSchema):
    expected_run_row_version: int = Field(ge=1, strict=True)
    blueprint_id: UUID
    blueprint_revision: int = Field(ge=1, strict=True)
    expected_blueprint_content_sha256: Sha256


class RejectCourseGenerationV1(StrictSchema):
    expected_run_row_version: int = Field(ge=1, strict=True)
    expected_review_content_sha256: Sha256
    reason_code: GenerationRejectionReason


class CanonicalizeCourseGenerationV1(StrictSchema):
    expected_run_row_version: int = Field(ge=1, strict=True)
    expected_output_manifest_sha256: Sha256
    course_slug: Annotated[
        str,
        Field(min_length=1, max_length=63, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
    ]


class GenerationCanonicalizationV1(StrictSchema):
    id: UUID
    tenant_id: UUID
    generation_run_id: UUID
    course_id: UUID
    course_version_id: UUID
    reviewed_output_sha256: Sha256
    canonical_content_sha256: Sha256
    canonicalization_sha256: Sha256
    canonicalized_by_actor_id: UUID
    created_at: datetime

    _created_timezone = field_validator("created_at")(_require_timezone)


class CourseGenerationRunV1(StrictSchema):
    id: UUID
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID
    ingestion_run_id: UUID
    supersedes_run_id: UUID | None
    status: GenerationStatus
    target_level: Literal["beginner", "intermediate", "advanced"]
    target_duration_minutes: int = Field(ge=1, le=10_000, strict=True)
    intended_audience: str = Field(min_length=1, max_length=300)
    teaching_style: Literal["concise", "guided", "reference"]
    locale: Literal["en"]
    adapter: Literal["deterministic-source-course-v1"]
    provider: Literal["local_deterministic"]
    model: Literal["none"]
    input_manifest_sha256: Sha256
    blueprint_content_sha256: Sha256 | None
    output_manifest_sha256: Sha256 | None
    attempt_count: int = Field(ge=0, le=10, strict=True)
    max_attempts: int = Field(ge=1, le=10, strict=True)
    checkpoint: str = Field(min_length=1, max_length=64)
    reason_code: str | None = Field(max_length=80)
    row_version: int = Field(ge=1, strict=True)
    created_at: datetime
    updated_at: datetime

    _created_timezone = field_validator("created_at")(_require_timezone)
    _updated_timezone = field_validator("updated_at")(_require_timezone)

    @model_validator(mode="after")
    def require_evidence_shape(self) -> Self:
        if self.attempt_count > self.max_attempts:
            raise ValueError("attempt count exceeds maximum")
        if self.status in {"queued", "planning"}:
            if self.blueprint_content_sha256 is not None or self.output_manifest_sha256 is not None:
                raise ValueError("planning state cannot expose generated evidence")
        elif self.status in {"blueprint_review", "generation_queued", "generating"}:
            if self.blueprint_content_sha256 is None or self.output_manifest_sha256 is not None:
                raise ValueError("blueprint state requires only blueprint evidence")
        elif self.status in {"review_ready", "canonicalized"}:
            if self.blueprint_content_sha256 is None or self.output_manifest_sha256 is None:
                raise ValueError("review state requires complete generated evidence")
        if self.status in {"retryable", "failed", "rights_blocked", "rejected"}:
            if self.reason_code is None:
                raise ValueError("failed state requires a stable reason")
        elif self.reason_code is not None:
            raise ValueError("active state cannot expose a failure reason")
        return self


class CourseBlueprintItemV1(StrictSchema):
    id: UUID
    kind: Literal["module", "lesson"]
    parent_id: UUID | None
    position: int = Field(ge=1, strict=True)
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(max_length=1000)
    source_section_id: UUID

    @model_validator(mode="after")
    def require_parent_shape(self) -> Self:
        if (self.kind == "module") != (self.parent_id is None):
            raise ValueError("only lessons have a parent")
        return self


class CourseBlueprintV1(StrictSchema):
    id: UUID
    schema_version: Literal["course-blueprint.v1"]
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(max_length=2000)
    intended_audience: str = Field(min_length=1, max_length=300)
    prerequisites: tuple[str, ...]
    learning_outcomes: tuple[str, ...]
    items: tuple[CourseBlueprintItemV1, ...]
    projection: dict[str, object]
    content_sha256: Sha256


class GeneratedLessonV1(StrictSchema):
    id: UUID
    schema_version: Literal["course-draft.v1"]
    blueprint_lesson_item_id: UUID
    source_section_id: UUID
    title: str = Field(min_length=1, max_length=160)
    document: dict[str, object]
    content_sha256: Sha256


class CourseGenerationReviewPackageV1(StrictSchema):
    run: CourseGenerationRunV1
    blueprint: CourseBlueprintV1 | None
    lessons: tuple[GeneratedLessonV1, ...]

    @model_validator(mode="after")
    def require_package_shape(self) -> Self:
        if (self.run.blueprint_content_sha256 is None) != (self.blueprint is None):
            raise ValueError("blueprint evidence does not match the run")
        if self.run.output_manifest_sha256 is None and self.lessons:
            raise ValueError("lessons require an output manifest")
        if self.run.output_manifest_sha256 is not None and not self.lessons:
            raise ValueError("output manifest requires generated lessons")
        return self


class CourseGenerationServiceV1(Protocol):
    def start_generation(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        command: StartCourseGenerationV1,
        idempotency_key: str,
    ) -> object: ...

    def get_generation(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        run_id: UUID,
    ) -> object: ...

    def approve_blueprint(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        run_id: UUID,
        command: ApproveGenerationBlueprintV1,
        idempotency_key: str,
    ) -> object: ...

    def reject_generation(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        run_id: UUID,
        command: RejectCourseGenerationV1,
        idempotency_key: str,
    ) -> object: ...

    def canonicalize_generation(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        run_id: UUID,
        command: CanonicalizeCourseGenerationV1,
        idempotency_key: str,
    ) -> object: ...
