from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import datetime
from typing import Annotated, Literal, Protocol, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.config import JsonDict
from pydantic.json_schema import SkipJsonSchema

CourseStatus = Literal[
    "draft",
    "under_review",
    "changes_requested",
    "approved",
    "scheduled",
    "published",
    "withdrawn",
    "archived",
]
CourseOrigin = Literal["manual", "ai_assisted"]
ReviewerPolicy = Literal["self_review_allowed", "separate_reviewer_required"]
TransitionName = Literal[
    "submit_review",
    "request_changes",
    "approve",
    "publish",
    "withdraw",
    "archive",
]
ReviewDecision = Literal["changes_requested", "approved"]
RichTextMark = Literal["strong", "emphasis", "code"]

Slug = Annotated[
    str,
    Field(min_length=1, max_length=63, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
]
Locale = Annotated[str, Field(max_length=10, pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$")]
Title = Annotated[str, Field(min_length=1, max_length=160)]
Description = Annotated[str, Field(min_length=1, max_length=2000)]
ContentHash = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
ReasonCode = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")]
PositiveInteger = Annotated[int, Field(ge=1, strict=True)]
ReasonCodeList = Annotated[list[ReasonCode], Field(min_length=1, max_length=20)]


def _omit_none_default(schema: JsonDict) -> None:
    schema.pop("default", None)


class CourseAdministrationError(Exception):
    """Stable service failure translated without trusting its human-readable fields."""

    def __init__(
        self,
        *,
        code: str,
        status: int = 500,
        title: str = "",
        detail: str = "",
        errors: Sequence[dict[str, object]] = (),
    ) -> None:
        super().__init__(code)
        self.code = code
        self.status = status
        self.title = title
        self.detail = detail
        self.errors = tuple(errors)


class VerifiedActorResult(Protocol):
    @property
    def principal_id(self) -> UUID: ...


class Positioned(Protocol):
    @property
    def position(self) -> int: ...


class StrictSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
    )


class TextNode(StrictSchema):
    type: Literal["text"]
    text: str = Field(min_length=1, max_length=10_000)
    marks: list[RichTextMark] = Field(max_length=3)

    @field_validator("marks")
    @classmethod
    def require_unique_marks(cls, value: list[RichTextMark]) -> list[RichTextMark]:
        if len(value) != len(set(value)):
            raise ValueError("marks must be unique")
        return value


class ParagraphNode(StrictSchema):
    type: Literal["paragraph"]
    content: list[TextNode] = Field(min_length=1, max_length=500)


class HeadingNode(StrictSchema):
    type: Literal["heading"]
    level: int = Field(ge=2, le=4, strict=True)
    content: list[TextNode] = Field(min_length=1, max_length=100)


class ListItemNode(StrictSchema):
    type: Literal["list_item"]
    content: list[ParagraphNode] = Field(min_length=1, max_length=20)


class BulletListNode(StrictSchema):
    type: Literal["bullet_list"]
    items: list[ListItemNode] = Field(min_length=1, max_length=100)


class OrderedListNode(StrictSchema):
    type: Literal["ordered_list"]
    items: list[ListItemNode] = Field(min_length=1, max_length=100)


RichTextBlockNode = Annotated[
    ParagraphNode | HeadingNode | BulletListNode | OrderedListNode,
    Field(discriminator="type"),
]


class RichTextDocument(StrictSchema):
    type: Literal["document"]
    content: list[RichTextBlockNode] = Field(min_length=1, max_length=500)


class CurriculumIdentity(StrictSchema):
    model_config = ConfigDict(
        json_schema_extra={
            "oneOf": [
                {"required": ["id", "expected_row_version"]},
                {
                    "not": {
                        "anyOf": [
                            {"required": ["id"]},
                            {"required": ["expected_row_version"]},
                        ]
                    }
                },
            ]
        }
    )

    id: UUID | SkipJsonSchema[None] = Field(
        default=None,
        json_schema_extra=_omit_none_default,
    )
    expected_row_version: PositiveInteger | SkipJsonSchema[None] = Field(
        default=None,
        json_schema_extra=_omit_none_default,
    )

    @model_validator(mode="after")
    def require_complete_identity_pair(self) -> Self:
        identity_fields = {"id", "expected_row_version"}
        supplied = identity_fields & self.model_fields_set
        if supplied and supplied != identity_fields:
            raise ValueError("id and expected_row_version must be supplied together")
        if supplied and (self.id is None or self.expected_row_version is None):
            raise ValueError("curriculum identity fields cannot be null")
        return self


class CurriculumBlockV1(CurriculumIdentity):
    kind: Literal["rich_text"]
    position: int = Field(ge=1, strict=True)
    document: RichTextDocument


class CurriculumLessonV1(CurriculumIdentity):
    title: Title
    position: int = Field(ge=1, strict=True)
    is_required: bool = Field(strict=True)
    content_blocks: list[CurriculumBlockV1] = Field(min_length=1, max_length=100)


class CurriculumSectionV1(CurriculumIdentity):
    title: Title
    position: int = Field(ge=1, strict=True)
    lessons: list[CurriculumLessonV1] = Field(min_length=1, max_length=200)


def _require_ordered_unique_positions(items: Sequence[Positioned], *, scope: str) -> None:
    positions = [item.position for item in items]
    if len(positions) != len(set(positions)):
        raise ValueError(f"{scope} positions must be unique")
    if positions != sorted(positions):
        raise ValueError(f"{scope} must be ordered by position")


def _require_unique_ids(items: Sequence[CurriculumIdentity], *, scope: str) -> None:
    identifiers = [item.id for item in items if item.id is not None]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError(f"{scope} ids must be unique")


class CreateCourseV1(StrictSchema):
    slug: Slug
    primary_locale: Locale
    title: Title
    description: Description


class UpdateCourseVersionV1(StrictSchema):
    model_config = ConfigDict(
        json_schema_extra={
            "minProperties": 2,
            "anyOf": [
                {"required": ["primary_locale"]},
                {"required": ["title"]},
                {"required": ["description"]},
            ],
        }
    )

    expected_version_row_version: int = Field(ge=1, strict=True)
    primary_locale: Locale | SkipJsonSchema[None] = Field(
        default=None,
        json_schema_extra=_omit_none_default,
    )
    title: Title | SkipJsonSchema[None] = Field(
        default=None,
        json_schema_extra=_omit_none_default,
    )
    description: Description | SkipJsonSchema[None] = Field(
        default=None,
        json_schema_extra=_omit_none_default,
    )

    @model_validator(mode="after")
    def require_non_null_patch(self) -> Self:
        patch_fields = {"primary_locale", "title", "description"}
        supplied = patch_fields & self.model_fields_set
        if not supplied:
            raise ValueError("at least one metadata field is required")
        if any(getattr(self, field) is None for field in supplied):
            raise ValueError("metadata fields cannot be null")
        return self


class ReplaceCurriculumV1(StrictSchema):
    expected_version_row_version: int = Field(ge=1, strict=True)
    sections: list[CurriculumSectionV1] = Field(max_length=100)

    @model_validator(mode="after")
    def require_ordered_unique_curriculum(self) -> Self:
        _require_ordered_unique_positions(self.sections, scope="section")
        _require_unique_ids(self.sections, scope="section")
        lessons: list[CurriculumLessonV1] = []
        blocks: list[CurriculumBlockV1] = []
        for section in self.sections:
            _require_ordered_unique_positions(section.lessons, scope="lesson")
            lessons.extend(section.lessons)
            for lesson in section.lessons:
                _require_ordered_unique_positions(
                    lesson.content_blocks,
                    scope="content block",
                )
                blocks.extend(lesson.content_blocks)
        _require_unique_ids(lessons, scope="lesson")
        _require_unique_ids(blocks, scope="content block")
        return self


class TransitionCourseVersionV1(StrictSchema):
    model_config = ConfigDict(
        json_schema_extra={
            "allOf": [
                {
                    "if": {
                        "properties": {"transition": {"const": "request_changes"}},
                        "required": ["transition"],
                    },
                    "then": {
                        "required": ["reason_codes"],
                        "not": {"required": ["reason_code"]},
                    },
                    "else": {"not": {"required": ["reason_codes"]}},
                },
                {
                    "if": {
                        "properties": {"transition": {"enum": ["withdraw", "archive"]}},
                        "required": ["transition"],
                    },
                    "then": {"required": ["reason_code"]},
                    "else": {"not": {"required": ["reason_code"]}},
                },
                {
                    "if": {
                        "properties": {"transition": {"enum": ["publish", "withdraw"]}},
                        "required": ["transition"],
                    },
                    "then": {"required": ["expected_course_row_version"]},
                    "else": {"not": {"required": ["expected_course_row_version"]}},
                },
            ]
        }
    )

    transition: TransitionName
    expected_version_row_version: int = Field(ge=1, strict=True)
    expected_course_row_version: PositiveInteger | SkipJsonSchema[None] = Field(
        default=None,
        json_schema_extra=_omit_none_default,
    )
    expected_content_hash: ContentHash
    reason_code: ReasonCode | SkipJsonSchema[None] = Field(
        default=None,
        json_schema_extra=_omit_none_default,
    )
    reason_codes: ReasonCodeList | SkipJsonSchema[None] = Field(
        default=None,
        json_schema_extra=_omit_none_default,
    )

    @field_validator("reason_codes")
    @classmethod
    def require_unique_reason_codes(cls, value: list[ReasonCode] | None) -> list[ReasonCode] | None:
        if value is not None and len(value) != len(set(value)):
            raise ValueError("reason_codes must be unique")
        return value

    @model_validator(mode="after")
    def require_transition_fields(self) -> Self:
        nullable_fields = {
            "expected_course_row_version",
            "reason_code",
            "reason_codes",
        }
        if any(
            field in self.model_fields_set and getattr(self, field) is None
            for field in nullable_fields
        ):
            raise ValueError("transition fields cannot be null")
        if self.transition == "request_changes":
            if self.reason_codes is None or self.reason_code is not None:
                raise ValueError("request_changes requires reason_codes only")
        elif self.reason_codes is not None:
            raise ValueError("reason_codes are valid only for request_changes")

        if self.transition in {"withdraw", "archive"}:
            if self.reason_code is None:
                raise ValueError("withdraw and archive require reason_code")
        elif self.reason_code is not None:
            raise ValueError("reason_code is valid only for withdraw or archive")

        if self.transition in {"publish", "withdraw"}:
            if self.expected_course_row_version is None:
                raise ValueError("publication pointer transitions require the course row version")
        elif self.expected_course_row_version is not None:
            raise ValueError("expected_course_row_version is not valid for this transition")
        return self


class CreateSuccessorDraftV1(StrictSchema):
    expected_course_row_version: int = Field(ge=1, strict=True)
    expected_source_version_row_version: int = Field(ge=1, strict=True)
    expected_source_content_hash: ContentHash


class CourseRecordV1(StrictSchema):
    id: UUID
    tenant_id: UUID
    slug: Slug
    reviewer_policy: ReviewerPolicy
    current_published_version_id: UUID | None
    instructor_membership_ids: list[UUID] = Field(min_length=1, max_length=20)
    row_version: int = Field(ge=1, strict=True)

    @field_validator("instructor_membership_ids")
    @classmethod
    def require_unique_instructors(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("instructor_membership_ids must be unique")
        return value


class CourseVersionRecordV1(StrictSchema):
    id: UUID
    tenant_id: UUID
    course_id: UUID
    predecessor_version_id: UUID | None
    version_number: int = Field(ge=1, strict=True)
    status: CourseStatus
    origin_type: CourseOrigin
    primary_locale: Locale
    title: Title
    description: Description
    content_hash: ContentHash
    submitted_hash: ContentHash | None
    approved_hash: ContentHash | None
    row_version: int = Field(ge=1, strict=True)


class ContentBlockRecordV1(StrictSchema):
    id: UUID
    tenant_id: UUID
    course_version_id: UUID
    lesson_id: UUID
    kind: Literal["rich_text"]
    position: int = Field(ge=1, strict=True)
    row_version: int = Field(ge=1, strict=True)
    document: RichTextDocument


class LessonRecordV1(StrictSchema):
    id: UUID
    tenant_id: UUID
    course_version_id: UUID
    section_id: UUID
    title: Title
    position: int = Field(ge=1, strict=True)
    is_required: bool = Field(strict=True)
    row_version: int = Field(ge=1, strict=True)
    content_blocks: list[ContentBlockRecordV1] = Field(min_length=1, max_length=100)


class SectionRecordV1(StrictSchema):
    id: UUID
    tenant_id: UUID
    course_version_id: UUID
    title: Title
    position: int = Field(ge=1, strict=True)
    row_version: int = Field(ge=1, strict=True)
    lessons: list[LessonRecordV1] = Field(min_length=1, max_length=200)


class CourseReviewV1(StrictSchema):
    id: UUID
    tenant_id: UUID
    course_version_id: UUID
    decision: ReviewDecision
    reviewed_hash: ContentHash
    reviewer_id: UUID
    self_review: bool = Field(strict=True)
    reason_codes: list[ReasonCode] = Field(max_length=20)
    decided_at: datetime

    @field_validator("reason_codes")
    @classmethod
    def require_unique_review_reasons(cls, value: list[ReasonCode]) -> list[ReasonCode]:
        if len(value) != len(set(value)):
            raise ValueError("reason_codes must be unique")
        return value

    @field_validator("decided_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("decided_at must include a timezone")
        return value


def _content_projection(snapshot: CourseSnapshotV1) -> dict[str, object]:
    return {
        "primary_locale": snapshot.version.primary_locale,
        "title": snapshot.version.title,
        "description": snapshot.version.description,
        "sections": [
            {
                "title": section.title,
                "position": section.position,
                "lessons": [
                    {
                        "title": lesson.title,
                        "position": lesson.position,
                        "is_required": lesson.is_required,
                        "content_blocks": [
                            {
                                "kind": block.kind,
                                "position": block.position,
                                "document": block.document.model_dump(mode="json"),
                            }
                            for block in lesson.content_blocks
                        ],
                    }
                    for lesson in section.lessons
                ],
            }
            for section in snapshot.sections
        ],
    }


def _canonical_content_hash(snapshot: CourseSnapshotV1) -> str:
    canonical_bytes = json.dumps(
        _content_projection(snapshot),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode()
    return f"sha256:{hashlib.sha256(canonical_bytes).hexdigest()}"


class CourseSnapshotV1(StrictSchema):
    schema_uri: Literal["https://contracts.ai-lms.local/f002/canonical-course.v1.schema.json"] = (
        Field(alias="$schema")
    )
    course: CourseRecordV1
    version: CourseVersionRecordV1
    sections: list[SectionRecordV1] = Field(max_length=100)
    latest_review: CourseReviewV1 | None

    @model_validator(mode="after")
    def require_consistent_snapshot_edges_and_hash(self) -> Self:
        tenant_id = self.course.tenant_id
        version_id = self.version.id
        if self.version.tenant_id != tenant_id or self.version.course_id != self.course.id:
            raise ValueError("version scope does not match course scope")
        if (
            self.course.current_published_version_id == version_id
            and self.version.status != "published"
        ):
            raise ValueError("current publication pointer must identify a published version")
        _require_ordered_unique_positions(self.sections, scope="section")
        if len({section.id for section in self.sections}) != len(self.sections):
            raise ValueError("section ids must be unique")
        lesson_ids: set[UUID] = set()
        block_ids: set[UUID] = set()
        for section in self.sections:
            if section.tenant_id != tenant_id or section.course_version_id != version_id:
                raise ValueError("section scope does not match snapshot scope")
            _require_ordered_unique_positions(section.lessons, scope="lesson")
            for lesson in section.lessons:
                if lesson.id in lesson_ids:
                    raise ValueError("lesson ids must be unique")
                lesson_ids.add(lesson.id)
                if (
                    lesson.tenant_id != tenant_id
                    or lesson.course_version_id != version_id
                    or lesson.section_id != section.id
                ):
                    raise ValueError("lesson scope does not match snapshot scope")
                _require_ordered_unique_positions(
                    lesson.content_blocks,
                    scope="content block",
                )
                for block in lesson.content_blocks:
                    if block.id in block_ids:
                        raise ValueError("content block ids must be unique")
                    block_ids.add(block.id)
                    if (
                        block.tenant_id != tenant_id
                        or block.course_version_id != version_id
                        or block.lesson_id != lesson.id
                    ):
                        raise ValueError("content block scope does not match snapshot scope")
        if self.latest_review is not None and (
            self.latest_review.tenant_id != tenant_id
            or self.latest_review.course_version_id != version_id
        ):
            raise ValueError("review scope does not match snapshot scope")
        if self.version.content_hash != _canonical_content_hash(self):
            raise ValueError("content_hash does not match canonical product content")
        return self


class CourseVersionSummaryV1(StrictSchema):
    id: UUID
    tenant_id: UUID
    course_id: UUID
    predecessor_version_id: UUID | None
    version_number: int = Field(ge=1, strict=True)
    status: CourseStatus
    title: Title
    content_hash: ContentHash
    row_version: int = Field(ge=1, strict=True)
    is_current_published: bool = Field(strict=True)


class CourseVersionHistoryV1(StrictSchema):
    tenant_id: UUID
    course_id: UUID
    current_published_version_id: UUID | None
    versions: list[CourseVersionSummaryV1] = Field(max_length=100)
    next_cursor: str | None = Field(min_length=1, max_length=2048)

    @model_validator(mode="after")
    def require_scoped_descending_history(self) -> Self:
        if any(
            version.tenant_id != self.tenant_id or version.course_id != self.course_id
            for version in self.versions
        ):
            raise ValueError("version history contains a mismatched scope")
        order = [(version.version_number, version.id.int) for version in self.versions]
        if order != sorted(order, reverse=True):
            raise ValueError("version history must use descending stable order")
        if len({version.id for version in self.versions}) != len(self.versions):
            raise ValueError("version history ids must be unique")
        current = [version.id for version in self.versions if version.is_current_published]
        if len(current) > 1 or (
            current
            and (
                self.current_published_version_id is None
                or current[0] != self.current_published_version_id
            )
        ):
            raise ValueError("published pointer does not match version history")
        for version in self.versions:
            if (
                version.id == self.current_published_version_id and not version.is_current_published
            ) or (version.is_current_published and version.status != "published"):
                raise ValueError("published version summary is inconsistent")
        return self


class SuccessorDraftResultV1(StrictSchema):
    source_version_id: UUID
    successor_version_id: UUID
    snapshot: CourseSnapshotV1

    @model_validator(mode="after")
    def require_matching_successor_snapshot(self) -> Self:
        if self.snapshot.version.id != self.successor_version_id:
            raise ValueError("successor id does not match snapshot")
        if self.snapshot.version.predecessor_version_id != self.source_version_id:
            raise ValueError("source id does not match successor predecessor")
        return self


class CourseAdministrationServiceV1(Protocol):
    """Structural service port shared by FastAPI and trusted Admin adapters."""

    def create_course(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        command: CreateCourseV1,
        idempotency_key: str,
    ) -> object: ...

    def get_course_version(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
    ) -> object: ...

    def list_course_versions(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> object: ...

    def update_version(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: UpdateCourseVersionV1,
    ) -> object: ...

    def replace_curriculum(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: ReplaceCurriculumV1,
    ) -> object: ...

    def transition_version(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: TransitionCourseVersionV1,
        idempotency_key: str,
    ) -> object: ...

    def create_successor_draft(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        source_version_id: UUID,
        command: CreateSuccessorDraftV1,
        idempotency_key: str,
    ) -> object: ...
