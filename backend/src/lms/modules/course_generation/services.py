from __future__ import annotations

import hashlib
import hmac
import json
import re
import uuid
from datetime import timedelta
from typing import Literal, Protocol, cast
from uuid import UUID

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from lms.modules.courses.errors import CourseLifecycleError
from lms.modules.courses.types import (
    ContentBlockInput,
    CourseSnapshot,
    CourseStatus,
    CreateAiAssistedDraftCommand,
    CurriculumSection,
    CurriculumSectionInput,
    Lesson,
    LessonInput,
    OriginType,
    RichTextBlock,
)
from lms.modules.courses.validation import validate_rich_text_document
from lms.modules.documents.models import (
    DocumentIngestionRun,
    DocumentSection,
    DocumentSectionElement,
    SourceDocument,
    SourceUseAuthorization,
    SourceVersion,
)
from lms.modules.tenancy.errors import TenancyError
from lms.modules.tenancy.models import AuditFact, IdempotencyReservation, OutboxFact
from lms.modules.tenancy.services import authorize_tenant_permission

from .adapter import (
    ADAPTER_VERSION,
    BLUEPRINT_SCHEMA_VERSION,
    COURSE_DRAFT_SCHEMA_VERSION,
    GENERATION_POLICY_VERSION,
    PROMPT_TEMPLATE_SHA256,
    DeterministicSourceCourseAdapter,
)
from .errors import CourseGenerationError, FieldError
from .models import (
    BlueprintReviewDecision,
    CanonicalizationSourceEdge,
    CourseBlueprint,
    CourseBlueprintItem,
    CourseGenerationAttempt,
    CourseGenerationRejection,
    CourseGenerationRun,
    GeneratedLessonArtifact,
    GenerationCanonicalization,
    GenerationRunSnapshot,
    GenerationSourceEdge,
)
from .policy import (
    PERMISSION_BLUEPRINT_REVIEW,
    PERMISSION_DRAFT_CANONICALIZE,
    PERMISSION_GENERATION_CREATE,
    PERMISSION_GENERATION_READ,
)
from .types import (
    ApproveBlueprintCommand,
    BlueprintDraft,
    BlueprintItemDraft,
    BlueprintItemKind,
    CanonicalizationRecord,
    CanonicalizeGenerationCommand,
    GeneratedLessonDraft,
    GenerationIntent,
    GenerationReviewPackage,
    GenerationRunRecord,
    GenerationWorkerResult,
    JsonObject,
    JsonValue,
    RejectGenerationCommand,
    SourceElementInput,
    SourceSectionInput,
    TargetLevel,
    TeachingStyle,
)

_LEASE_SECONDS = 300
_WORKER_ACTOR_ID = uuid.uuid5(uuid.NAMESPACE_URL, "ai-lms:service:course-generation")
_TERMINAL_STATES = frozenset({"canonicalized", "rejected", "failed", "rights_blocked"})
_WORKER_STATES = frozenset({"planning", "generating"})
_RETRYABLE_REASON_CODES = frozenset({"GENERATION_ADAPTER_FAILED"})
_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class _RightsBlockedError(Exception):
    pass


class CourseDraftCanonicalizationPort(Protocol):
    def create_ai_assisted_draft(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        command: CreateAiAssistedDraftCommand,
        idempotency_key: str,
    ) -> CourseSnapshot: ...


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        default=str,
    ).encode("utf-8")


def _manifest_hash(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(value)).hexdigest()}"


def _request_hash(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _secret_digest(value: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _stable_id(*parts: object) -> UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, "ai-lms:" + ":".join(str(part) for part in parts))


def _set_worker_context(*, tenant_id: UUID, run_id: UUID, stage: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT set_config('app.current_actor_id', %s, true),
                   set_config('app.current_tenant_id', %s, true),
                   set_config('app.current_job_id', %s, true),
                   set_config('app.current_job_stage', %s, true)
            """,
            [str(_WORKER_ACTOR_ID), str(tenant_id), str(run_id), f"generation_{stage}"],
        )


def _translate_tenancy(error: TenancyError) -> CourseGenerationError:
    if error.code == "TENANT_ACCESS_INACTIVE":
        return CourseGenerationError("TENANT_ACCESS_INACTIVE")
    if error.code == "TENANT_PERMISSION_DENIED":
        return CourseGenerationError("GENERATION_PERMISSION_DENIED")
    return CourseGenerationError("GENERATION_RESOURCE_NOT_FOUND")


def _as_json_object(value: object) -> JsonObject:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise CourseGenerationError("SERVICE_CONTRACT_ERROR")
    return cast(JsonObject, value)


def _as_string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise CourseGenerationError("SERVICE_CONTRACT_ERROR")
    return tuple(value)


class CourseGenerationService:
    """Durable deterministic generation boundary shared by API, Admin, and worker."""

    def __init__(
        self,
        *,
        adapter: DeterministicSourceCourseAdapter | None = None,
        course_drafts: CourseDraftCanonicalizationPort | None = None,
    ) -> None:
        self._adapter = adapter or DeterministicSourceCourseAdapter()
        self._course_drafts = course_drafts

    @staticmethod
    def _authorize(*, actor_id: UUID, tenant_id: UUID, permission: str) -> None:
        try:
            authorize_tenant_permission(actor_id, tenant_id, permission)
        except TenancyError as error:
            raise _translate_tenancy(error) from error

    @staticmethod
    def _validate_idempotency_key(key: str) -> None:
        if not 16 <= len(key) <= 128 or key != key.strip():
            raise CourseGenerationError(
                "GENERATION_VALIDATION_FAILED",
                field_errors=(FieldError("idempotency_key", "invalid"),),
            )

    @staticmethod
    def _validate_intent(intent: GenerationIntent) -> GenerationIntent:
        errors: list[FieldError] = []
        if intent.target_level not in {"beginner", "intermediate", "advanced"}:
            errors.append(FieldError("target_level", "unsupported"))
        if not 1 <= intent.target_duration_minutes <= 10_000:
            errors.append(FieldError("target_duration_minutes", "out_of_range"))
        audience = intent.intended_audience.strip()
        if not 1 <= len(audience) <= 300:
            errors.append(FieldError("intended_audience", "invalid_length"))
        if intent.teaching_style not in {"concise", "guided", "reference"}:
            errors.append(FieldError("teaching_style", "unsupported"))
        if intent.locale != "en":
            errors.append(FieldError("locale", "unsupported"))
        if errors:
            raise CourseGenerationError("GENERATION_VALIDATION_FAILED", field_errors=tuple(errors))
        return GenerationIntent(
            target_level=intent.target_level,
            target_duration_minutes=intent.target_duration_minutes,
            intended_audience=audience,
            teaching_style=intent.teaching_style,
            locale=intent.locale,
            supersedes_run_id=intent.supersedes_run_id,
        )

    @classmethod
    def _reserve_idempotency(
        cls,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        key: str,
        request: object,
        operation: str = PERMISSION_GENERATION_CREATE,
    ) -> tuple[IdempotencyReservation, dict[str, object] | None]:
        cls._validate_idempotency_key(key)
        digest = _request_hash(request)
        reservation, created = IdempotencyReservation.objects.select_for_update().get_or_create(
            tenant_id=tenant_id,
            actor_id=actor_id,
            operation=operation,
            key_digest=_secret_digest(key),
            defaults={"request_hash": digest},
        )
        if reservation.request_hash != digest:
            raise CourseGenerationError("IDEMPOTENCY_CONFLICT")
        if not created and reservation.status == "completed":
            if not isinstance(reservation.response_payload, dict):
                raise CourseGenerationError("SERVICE_CONTRACT_ERROR")
            return reservation, reservation.response_payload
        if not created:
            raise CourseGenerationError("GENERATION_STATE_CONFLICT")
        return reservation, None

    @staticmethod
    def _complete_idempotency(
        reservation: IdempotencyReservation,
        *,
        payload: dict[str, object],
    ) -> None:
        reservation.status = "completed"
        reservation.response_payload = payload
        reservation.save(update_fields=("status", "response_payload", "updated_at"))

    @classmethod
    def _complete_run_idempotency(
        cls,
        reservation: IdempotencyReservation,
        *,
        run: CourseGenerationRun,
    ) -> None:
        cls._complete_idempotency(
            reservation,
            payload={
                "resource_id": str(run.id),
                "source_document_id": str(run.source_document_id),
                "source_version_id": str(run.source_version_id),
                "ingestion_run_id": str(run.ingestion_run_id),
            },
        )

    @staticmethod
    def _authorization_is_active(authorization: SourceUseAuthorization) -> bool:
        now = timezone.now()
        return (
            authorization.status == "active"
            and authorization.valid_from is not None
            and authorization.valid_from <= now
            and (authorization.valid_until is None or authorization.valid_until > now)
        )

    @staticmethod
    def _record(run: CourseGenerationRun) -> GenerationRunRecord:
        return GenerationRunRecord(
            id=run.id,
            tenant_id=run.tenant_id,
            source_document_id=run.source_document_id,
            source_version_id=run.source_version_id,
            ingestion_run_id=run.ingestion_run_id,
            supersedes_run_id=run.supersedes_run_id,
            status=run.status,
            target_level=run.target_level,
            target_duration_minutes=run.target_duration_minutes,
            intended_audience=run.intended_audience,
            teaching_style=run.teaching_style,
            locale=run.locale,
            adapter=run.adapter,
            provider=run.provider,
            model=run.model,
            input_manifest_sha256=run.input_manifest_sha256,
            blueprint_content_sha256=run.blueprint_content_sha256,
            output_manifest_sha256=run.output_manifest_sha256,
            attempt_count=run.attempt_count,
            max_attempts=run.max_attempts,
            checkpoint=run.checkpoint,
            reason_code=run.reason_code,
            row_version=run.row_version,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    @staticmethod
    def _record_fact(
        *,
        actor_id: UUID,
        run: CourseGenerationRun,
        event_type: str,
    ) -> None:
        request_id = uuid.uuid4()
        now = timezone.now()
        safe_payload: dict[str, JsonValue] = {
            "course_generation_run_id": str(run.id),
            "source_document_id": str(run.source_document_id),
            "source_version_id": str(run.source_version_id),
            "ingestion_run_id": str(run.ingestion_run_id),
            "status": run.status,
            "checkpoint": run.checkpoint,
            "reason_code": run.reason_code,
            "input_manifest_sha256": run.input_manifest_sha256,
            "blueprint_content_sha256": run.blueprint_content_sha256,
            "output_manifest_sha256": run.output_manifest_sha256,
            "attempt_count": run.attempt_count,
            "row_version": run.row_version,
        }
        AuditFact.objects.create(
            tenant_id=run.tenant_id,
            event_type=event_type,
            actor_id=actor_id,
            subject_type="course_generation_run",
            subject_id=run.id,
            request_id=request_id,
            payload=safe_payload,
        )
        OutboxFact.objects.create(
            tenant_id=run.tenant_id,
            event_type=event_type,
            aggregate_type="course_generation_run",
            aggregate_id=run.id,
            actor_id=actor_id,
            request_id=request_id,
            payload={
                "event_version": 1,
                "producer": "course_generation",
                "recorded_at": now.isoformat(),
                "privacy_class": "internal",
                **safe_payload,
            },
        )

    @staticmethod
    def _record_review_audit(
        *,
        actor_id: UUID,
        run: CourseGenerationRun,
        event_type: str,
        reviewed_content_sha256: str,
    ) -> None:
        AuditFact.objects.create(
            tenant_id=run.tenant_id,
            event_type=event_type,
            actor_id=actor_id,
            subject_type="course_generation_run",
            subject_id=run.id,
            request_id=uuid.uuid4(),
            payload={
                "course_generation_run_id": str(run.id),
                "reviewed_content_sha256": reviewed_content_sha256,
                "status": run.status,
                "row_version": run.row_version,
            },
        )

    @staticmethod
    def _section_hash(section: DocumentSection, edges: tuple[DocumentSectionElement, ...]) -> str:
        return _manifest_hash(
            {
                "id": str(section.id),
                "position": section.position,
                "title": section.title,
                "start_page": section.start_page,
                "end_page": section.end_page,
                "elements": [
                    {
                        "id": str(edge.element_id),
                        "position": edge.position,
                        "kind": edge.element.kind,
                        "text_sha256": edge.element.text_sha256,
                    }
                    for edge in edges
                ],
            }
        )

    @classmethod
    def _load_source_sections(
        cls,
        *,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        ingestion_run_id: UUID,
    ) -> tuple[SourceSectionInput, ...]:
        sections = tuple(
            DocumentSection.objects.filter(
                tenant_id=tenant_id,
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                created_by_run_id=ingestion_run_id,
            ).order_by("position", "id")
        )
        if not 1 <= len(sections) <= 100 or [section.position for section in sections] != list(
            range(1, len(sections) + 1)
        ):
            raise CourseGenerationError("GENERATION_SOURCE_INVALID")
        loaded: list[SourceSectionInput] = []
        for section in sections:
            edges = tuple(
                DocumentSectionElement.objects.select_related("element")
                .filter(
                    tenant_id=tenant_id,
                    source_version_id=source_version_id,
                    section_id=section.id,
                )
                .order_by("position", "id")
            )
            if not edges or [edge.position for edge in edges] != list(range(1, len(edges) + 1)):
                raise CourseGenerationError("GENERATION_SOURCE_INVALID")
            elements: list[SourceElementInput] = []
            for edge in edges:
                element = edge.element
                if (
                    element.tenant_id != tenant_id
                    or element.source_document_id != source_document_id
                    or element.source_version_id != source_version_id
                    or element.created_by_run_id != ingestion_run_id
                    or element.kind not in {"heading", "paragraph"}
                    or not element.text.strip()
                    or len(element.text) > 10_000
                ):
                    raise CourseGenerationError("GENERATION_SOURCE_INVALID")
                elements.append(
                    SourceElementInput(
                        id=element.id,
                        position=edge.position,
                        kind=cast(Literal["heading", "paragraph"], element.kind),
                        text=element.text,
                        text_sha256=element.text_sha256,
                    )
                )
            loaded.append(
                SourceSectionInput(
                    id=section.id,
                    position=section.position,
                    title=section.title,
                    content_sha256=cls._section_hash(section, edges),
                    elements=tuple(elements),
                )
            )
        return tuple(loaded)

    @staticmethod
    def _intent_from_run(run: CourseGenerationRun) -> GenerationIntent:
        return GenerationIntent(
            target_level=cast(TargetLevel, run.target_level),
            target_duration_minutes=run.target_duration_minutes,
            intended_audience=run.intended_audience,
            teaching_style=cast(TeachingStyle, run.teaching_style),
            locale="en",
            supersedes_run_id=run.supersedes_run_id,
        )

    @staticmethod
    def _blueprint_record(blueprint: CourseBlueprint) -> BlueprintDraft:
        items = tuple(
            BlueprintItemDraft(
                id=item.id,
                kind=cast(BlueprintItemKind, item.kind),
                parent_id=item.parent_id,
                position=item.position,
                title=item.title,
                description=item.description,
                source_section_id=item.source_section_id,
            )
            for item in blueprint.items.order_by("kind", "position", "id")
        )
        return BlueprintDraft(
            id=blueprint.id,
            schema_version="course-blueprint.v1",
            title=blueprint.title,
            description=blueprint.description,
            intended_audience=blueprint.intended_audience,
            prerequisites=_as_string_tuple(blueprint.prerequisites),
            learning_outcomes=_as_string_tuple(blueprint.learning_outcomes),
            items=items,
            projection=_as_json_object(blueprint.projection),
            content_sha256=blueprint.content_sha256,
        )

    @staticmethod
    def _lesson_record(artifact: GeneratedLessonArtifact) -> GeneratedLessonDraft:
        return GeneratedLessonDraft(
            id=artifact.id,
            schema_version="course-draft.v1",
            blueprint_lesson_item_id=artifact.blueprint_item_id,
            source_section_id=artifact.source_section_id,
            title=artifact.title,
            document=_as_json_object(artifact.document),
            content_sha256=artifact.content_sha256,
        )

    def start_generation(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        ingestion_run_id: UUID,
        intent: GenerationIntent,
        idempotency_key: str,
    ) -> GenerationRunRecord:
        normalized_intent = self._validate_intent(intent)
        request = {
            "source_document_id": source_document_id,
            "source_version_id": source_version_id,
            "ingestion_run_id": ingestion_run_id,
            "adapter": ADAPTER_VERSION,
            "target_level": normalized_intent.target_level,
            "target_duration_minutes": normalized_intent.target_duration_minutes,
            "intended_audience": normalized_intent.intended_audience,
            "teaching_style": normalized_intent.teaching_style,
            "locale": normalized_intent.locale,
            "supersedes_run_id": normalized_intent.supersedes_run_id,
        }
        with transaction.atomic():
            self._authorize(
                actor_id=actor_id,
                tenant_id=tenant_id,
                permission=PERMISSION_GENERATION_CREATE,
            )
            reservation, replay = self._reserve_idempotency(
                actor_id=actor_id,
                tenant_id=tenant_id,
                key=idempotency_key,
                request=request,
            )
            if replay is not None:
                try:
                    run = CourseGenerationRun.objects.get(
                        tenant_id=tenant_id,
                        source_document_id=source_document_id,
                        source_version_id=source_version_id,
                        ingestion_run_id=ingestion_run_id,
                        id=UUID(str(replay["resource_id"])),
                    )
                except (KeyError, ValueError, CourseGenerationRun.DoesNotExist) as error:
                    raise CourseGenerationError("SERVICE_CONTRACT_ERROR") from error
                return self._record(run)
            try:
                document = SourceDocument.objects.select_for_update().get(
                    tenant_id=tenant_id,
                    id=source_document_id,
                    current_version_id=source_version_id,
                )
                version = SourceVersion.objects.get(
                    tenant_id=tenant_id,
                    source_document_id=source_document_id,
                    id=source_version_id,
                    admission_status="admitted",
                )
                ingestion_run = DocumentIngestionRun.objects.get(
                    tenant_id=tenant_id,
                    source_document_id=source_document_id,
                    source_version_id=source_version_id,
                    id=ingestion_run_id,
                    status="ready_for_generation",
                )
            except (
                DocumentIngestionRun.DoesNotExist,
                SourceDocument.DoesNotExist,
                SourceVersion.DoesNotExist,
            ) as error:
                raise CourseGenerationError("GENERATION_RESOURCE_NOT_FOUND") from error
            try:
                authorization = SourceUseAuthorization.objects.get(
                    tenant_id=tenant_id,
                    source_document_id=source_document_id,
                    source_version_id=source_version_id,
                    operation="generate",
                )
            except SourceUseAuthorization.DoesNotExist as error:
                raise CourseGenerationError("GENERATION_RIGHTS_REQUIRED") from error
            if not self._authorization_is_active(authorization):
                raise CourseGenerationError("GENERATION_RIGHTS_INACTIVE")
            if normalized_intent.supersedes_run_id is not None:
                try:
                    CourseGenerationRun.objects.get(
                        tenant_id=tenant_id,
                        id=normalized_intent.supersedes_run_id,
                        source_document_id=source_document_id,
                        source_version_id=source_version_id,
                        ingestion_run_id=ingestion_run_id,
                        status__in=("rejected", "canonicalized"),
                    )
                except CourseGenerationRun.DoesNotExist as error:
                    raise CourseGenerationError("GENERATION_STATE_CONFLICT") from error
            active = (
                CourseGenerationRun.objects.filter(
                    tenant_id=tenant_id,
                    ingestion_run_id=ingestion_run_id,
                    adapter=ADAPTER_VERSION,
                    status__in=(
                        "queued",
                        "planning",
                        "blueprint_review",
                        "generation_queued",
                        "generating",
                        "review_ready",
                        "retryable",
                    ),
                )
                .order_by("created_at", "id")
                .first()
            )
            if active is not None:
                self._complete_run_idempotency(reservation, run=active)
                return self._record(active)

            sections = self._load_source_sections(
                tenant_id=tenant_id,
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                ingestion_run_id=ingestion_run_id,
            )
            input_projection = {
                "adapter": ADAPTER_VERSION,
                "normalized_schema_version": "normalized-source.v1",
                "blueprint_schema_version": BLUEPRINT_SCHEMA_VERSION,
                "draft_schema_version": COURSE_DRAFT_SCHEMA_VERSION,
                "policy_version": GENERATION_POLICY_VERSION,
                "provider": self._adapter.provider,
                "model": self._adapter.model,
                "prompt_template_sha256": PROMPT_TEMPLATE_SHA256,
                "source_document_id": str(document.id),
                "source_version_id": str(version.id),
                "ingestion_run_id": str(ingestion_run.id),
                "ingestion_output_manifest_sha256": ingestion_run.output_manifest_sha256,
                "ordered_normalized_sections": [
                    {"id": str(section.id), "content_sha256": section.content_sha256}
                    for section in sections
                ],
                "intent": {
                    "target_level": normalized_intent.target_level,
                    "target_duration_minutes": normalized_intent.target_duration_minutes,
                    "intended_audience": normalized_intent.intended_audience,
                    "teaching_style": normalized_intent.teaching_style,
                    "locale": normalized_intent.locale,
                    "supersedes_run_id": (
                        None
                        if normalized_intent.supersedes_run_id is None
                        else str(normalized_intent.supersedes_run_id)
                    ),
                },
                "input_token_count": 0,
                "output_token_count": 0,
                "cost_minor_units": 0,
            }
            input_manifest_sha256 = _manifest_hash(input_projection)
            run = CourseGenerationRun.objects.create(
                tenant_id=tenant_id,
                source_document=document,
                source_version=version,
                ingestion_run=ingestion_run,
                generate_authorization=authorization,
                supersedes_run_id=normalized_intent.supersedes_run_id,
                requested_by_actor_id=actor_id,
                target_level=normalized_intent.target_level,
                target_duration_minutes=normalized_intent.target_duration_minutes,
                intended_audience=normalized_intent.intended_audience,
                teaching_style=normalized_intent.teaching_style,
                locale=normalized_intent.locale,
                adapter=ADAPTER_VERSION,
                provider=self._adapter.provider,
                model=self._adapter.model,
                normalized_schema_version="normalized-source.v1",
                blueprint_schema_version=BLUEPRINT_SCHEMA_VERSION,
                draft_schema_version=COURSE_DRAFT_SCHEMA_VERSION,
                policy_version=GENERATION_POLICY_VERSION,
                prompt_template_sha256=PROMPT_TEMPLATE_SHA256,
                input_manifest_sha256=input_manifest_sha256,
            )
            GenerationRunSnapshot.objects.create(
                id=_stable_id("generation-run-snapshot", run.id),
                tenant_id=tenant_id,
                generation_run=run,
                metadata=input_projection,
                content_sha256=input_manifest_sha256,
            )
            self._record_fact(
                actor_id=actor_id,
                run=run,
                event_type="course_generation.requested.v1",
            )
            self._complete_run_idempotency(reservation, run=run)
            return self._record(run)

    def get_generation(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        run_id: UUID,
    ) -> GenerationReviewPackage:
        with transaction.atomic():
            self._authorize(
                actor_id=actor_id,
                tenant_id=tenant_id,
                permission=PERMISSION_GENERATION_READ,
            )
            try:
                run = CourseGenerationRun.objects.get(tenant_id=tenant_id, id=run_id)
            except CourseGenerationRun.DoesNotExist as error:
                raise CourseGenerationError("GENERATION_RESOURCE_NOT_FOUND") from error
            blueprint_model = (
                CourseBlueprint.objects.filter(tenant_id=tenant_id, generation_run_id=run.id)
                .order_by("-revision")
                .first()
            )
            artifacts = tuple(
                GeneratedLessonArtifact.objects.filter(
                    tenant_id=tenant_id, generation_run_id=run.id
                ).order_by("blueprint_item__position", "id")
            )
            return GenerationReviewPackage(
                run=self._record(run),
                blueprint=(
                    None if blueprint_model is None else self._blueprint_record(blueprint_model)
                ),
                lessons=tuple(self._lesson_record(artifact) for artifact in artifacts),
            )

    @classmethod
    def _active_generate_authorization(cls, run: CourseGenerationRun) -> bool:
        try:
            authorization = SourceUseAuthorization.objects.get(
                tenant_id=run.tenant_id,
                source_document_id=run.source_document_id,
                source_version_id=run.source_version_id,
                id=run.generate_authorization_id,
                operation="generate",
            )
            SourceVersion.objects.get(
                tenant_id=run.tenant_id,
                source_document_id=run.source_document_id,
                id=run.source_version_id,
                admission_status="admitted",
            )
            DocumentIngestionRun.objects.get(
                tenant_id=run.tenant_id,
                source_document_id=run.source_document_id,
                source_version_id=run.source_version_id,
                id=run.ingestion_run_id,
                status="ready_for_generation",
            )
        except (
            DocumentIngestionRun.DoesNotExist,
            SourceUseAuthorization.DoesNotExist,
            SourceVersion.DoesNotExist,
        ):
            return False
        return cls._authorization_is_active(authorization)

    def _claim(
        self,
        *,
        tenant_id: UUID,
        run_id: UUID,
        worker_id: str,
    ) -> tuple[CourseGenerationRun, CourseGenerationAttempt | None, bool]:
        normalized_worker = worker_id.strip()
        if not 1 <= len(normalized_worker) <= 80:
            raise CourseGenerationError("GENERATION_LEASE_CONFLICT")
        with transaction.atomic():
            _set_worker_context(tenant_id=tenant_id, run_id=run_id, stage="claim")
            try:
                run = CourseGenerationRun.objects.select_for_update().get(
                    tenant_id=tenant_id, id=run_id
                )
            except CourseGenerationRun.DoesNotExist as error:
                raise CourseGenerationError("GENERATION_RESOURCE_NOT_FOUND") from error
            if run.status in _TERMINAL_STATES or run.status in {
                "blueprint_review",
                "review_ready",
            }:
                return run, None, False
            now = timezone.now()
            if run.status in _WORKER_STATES:
                if run.lease_expires_at is None or run.lease_expires_at > now:
                    raise CourseGenerationError("GENERATION_LEASE_CONFLICT")
                CourseGenerationAttempt.objects.filter(
                    tenant_id=tenant_id,
                    generation_run_id=run.id,
                    outcome="running",
                ).update(
                    outcome="retryable",
                    reason_code="GENERATION_LEASE_CONFLICT",
                    checkpoint="lease_expired",
                    completed_at=now,
                )
                run.status = "retryable"
                run.reason_code = "GENERATION_LEASE_CONFLICT"
                run.checkpoint = "lease_expired"
                run.lease_owner = None
                run.lease_expires_at = None
                run.heartbeat_at = now
                run.row_version += 1
                run.save()
            elif run.status not in {"queued", "generation_queued", "retryable"}:
                raise CourseGenerationError("GENERATION_STATE_CONFLICT")
            if run.attempt_count >= run.max_attempts:
                run.status = "failed"
                run.reason_code = "GENERATION_RETRY_EXHAUSTED"
                run.checkpoint = "retry_exhausted"
                run.row_version += 1
                run.save(
                    update_fields=(
                        "status",
                        "reason_code",
                        "checkpoint",
                        "row_version",
                        "updated_at",
                    )
                )
                self._record_fact(
                    actor_id=_WORKER_ACTOR_ID,
                    run=run,
                    event_type="course_generation.rejected.v1",
                )
                return run, None, False
            if not self._active_generate_authorization(run):
                run.status = "rights_blocked"
                run.reason_code = "GENERATION_RIGHTS_INACTIVE"
                run.checkpoint = "rights_blocked"
                run.lease_owner = None
                run.lease_expires_at = None
                run.row_version += 1
                run.save()
                self._record_fact(
                    actor_id=_WORKER_ACTOR_ID,
                    run=run,
                    event_type="course_generation.rejected.v1",
                )
                return run, None, False
            approved_blueprint_exists = CourseBlueprint.objects.filter(
                tenant_id=tenant_id,
                generation_run_id=run.id,
                status="approved",
            ).exists()
            stage = (
                "generating"
                if run.status == "generation_queued" or approved_blueprint_exists
                else "planning"
            )
            run.status = stage
            run.reason_code = None
            run.attempt_count += 1
            run.lease_owner = normalized_worker
            run.lease_expires_at = now + timedelta(seconds=_LEASE_SECONDS)
            run.heartbeat_at = now
            run.checkpoint = f"{stage}_claimed"
            run.row_version += 1
            run.save()
            attempt = CourseGenerationAttempt.objects.create(
                tenant_id=tenant_id,
                generation_run=run,
                attempt_number=run.attempt_count,
                stage=stage,
                checkpoint=run.checkpoint,
                input_manifest_sha256=run.input_manifest_sha256,
                started_at=now,
            )
            return run, attempt, True

    @staticmethod
    def _validate_blueprint(
        *,
        run: CourseGenerationRun,
        blueprint: BlueprintDraft,
        sections: tuple[SourceSectionInput, ...],
    ) -> None:
        section_ids = {section.id for section in sections}
        if (
            blueprint.schema_version != BLUEPRINT_SCHEMA_VERSION
            or blueprint.id != _stable_id("generation-blueprint", run.id, 1)
            or blueprint.content_sha256 != _manifest_hash(blueprint.projection)
            or len(blueprint.items) != len(sections) * 2
            or not blueprint.title.strip()
        ):
            raise CourseGenerationError("GENERATION_OUTPUT_INVALID")
        modules = {item.id: item for item in blueprint.items if item.kind == "module"}
        lessons = tuple(item for item in blueprint.items if item.kind == "lesson")
        if (
            len(modules) != len(sections)
            or len(lessons) != len(sections)
            or {item.source_section_id for item in blueprint.items} != section_ids
        ):
            raise CourseGenerationError("GENERATION_SOURCE_EDGE_INVALID")
        for lesson in lessons:
            parent = modules.get(lesson.parent_id) if lesson.parent_id is not None else None
            if parent is None or parent.source_section_id != lesson.source_section_id:
                raise CourseGenerationError("GENERATION_SOURCE_EDGE_INVALID")

    @staticmethod
    def _validate_lessons(
        *,
        blueprint: BlueprintDraft,
        lessons: tuple[GeneratedLessonDraft, ...],
        sections: tuple[SourceSectionInput, ...],
    ) -> None:
        expected_items = {item.id: item for item in blueprint.items if item.kind == "lesson"}
        section_ids = {section.id for section in sections}
        if len(lessons) != len(expected_items) or {
            lesson.blueprint_lesson_item_id for lesson in lessons
        } != set(expected_items):
            raise CourseGenerationError("GENERATION_OUTPUT_INVALID")
        for lesson in lessons:
            item = expected_items[lesson.blueprint_lesson_item_id]
            projection = {
                "schema_version": COURSE_DRAFT_SCHEMA_VERSION,
                "id": str(lesson.id),
                "blueprint_lesson_item_id": str(lesson.blueprint_lesson_item_id),
                "source_section_id": str(lesson.source_section_id),
                "title": lesson.title,
                "document": lesson.document,
            }
            if (
                lesson.schema_version != COURSE_DRAFT_SCHEMA_VERSION
                or lesson.source_section_id not in section_ids
                or lesson.source_section_id != item.source_section_id
                or lesson.content_sha256 != _manifest_hash(projection)
            ):
                raise CourseGenerationError("GENERATION_SOURCE_EDGE_INVALID")
            try:
                validate_rich_text_document(lesson.document)
            except ValueError as error:
                raise CourseGenerationError("GENERATION_OUTPUT_INVALID") from error

    def _finish_failure(
        self,
        *,
        tenant_id: UUID,
        run_id: UUID,
        worker_id: str,
        reason_code: str,
        retryable: bool,
        rights_blocked: bool = False,
    ) -> CourseGenerationRun:
        with transaction.atomic():
            _set_worker_context(tenant_id=tenant_id, run_id=run_id, stage="finish")
            try:
                run = CourseGenerationRun.objects.select_for_update().get(
                    tenant_id=tenant_id, id=run_id
                )
                attempt = CourseGenerationAttempt.objects.select_for_update().get(
                    tenant_id=tenant_id,
                    generation_run_id=run.id,
                    attempt_number=run.attempt_count,
                    outcome="running",
                )
            except (
                CourseGenerationAttempt.DoesNotExist,
                CourseGenerationRun.DoesNotExist,
            ) as error:
                raise CourseGenerationError("GENERATION_STATE_CONFLICT") from error
            if run.status not in _WORKER_STATES or run.lease_owner != worker_id.strip():
                raise CourseGenerationError("GENERATION_LEASE_CONFLICT")
            exhausted = retryable and run.attempt_count >= run.max_attempts
            run.status = (
                "rights_blocked"
                if rights_blocked
                else "failed"
                if exhausted or not retryable
                else "retryable"
            )
            run.reason_code = "GENERATION_RETRY_EXHAUSTED" if exhausted else reason_code
            run.checkpoint = (
                "rights_blocked" if rights_blocked else "retry_exhausted" if exhausted else "failed"
            )
            run.lease_owner = None
            run.lease_expires_at = None
            run.heartbeat_at = timezone.now()
            run.row_version += 1
            run.save()
            attempt.outcome = (
                "rights_blocked"
                if rights_blocked
                else "retryable"
                if run.status == "retryable"
                else "failed"
            )
            attempt.reason_code = reason_code
            attempt.checkpoint = run.checkpoint
            attempt.observation = {"reason_code": reason_code}
            attempt.completed_at = timezone.now()
            attempt.save()
            self._record_fact(
                actor_id=_WORKER_ACTOR_ID,
                run=run,
                event_type="course_generation.rejected.v1",
            )
            return run

    def _persist_blueprint(
        self,
        *,
        tenant_id: UUID,
        run_id: UUID,
        worker_id: str,
        blueprint: BlueprintDraft,
    ) -> CourseGenerationRun:
        with transaction.atomic():
            _set_worker_context(tenant_id=tenant_id, run_id=run_id, stage="blueprint_commit")
            try:
                run = CourseGenerationRun.objects.select_for_update().get(
                    tenant_id=tenant_id, id=run_id
                )
                attempt = CourseGenerationAttempt.objects.select_for_update().get(
                    tenant_id=tenant_id,
                    generation_run_id=run.id,
                    attempt_number=run.attempt_count,
                    outcome="running",
                )
            except (
                CourseGenerationAttempt.DoesNotExist,
                CourseGenerationRun.DoesNotExist,
            ) as error:
                raise CourseGenerationError("GENERATION_STATE_CONFLICT") from error
            now = timezone.now()
            if (
                run.status != "planning"
                or run.lease_owner != worker_id.strip()
                or run.lease_expires_at is None
                or run.lease_expires_at <= now
            ):
                raise CourseGenerationError("GENERATION_LEASE_CONFLICT")
            if not self._active_generate_authorization(run):
                raise _RightsBlockedError
            blueprint_model = CourseBlueprint.objects.create(
                id=blueprint.id,
                tenant_id=tenant_id,
                generation_run=run,
                revision=1,
                schema_version=blueprint.schema_version,
                title=blueprint.title,
                description=blueprint.description,
                intended_audience=blueprint.intended_audience,
                prerequisites=list(blueprint.prerequisites),
                learning_outcomes=list(blueprint.learning_outcomes),
                projection=blueprint.projection,
                content_sha256=blueprint.content_sha256,
            )
            item_models: dict[UUID, CourseBlueprintItem] = {}
            for item in blueprint.items:
                item_model = CourseBlueprintItem.objects.create(
                    id=item.id,
                    tenant_id=tenant_id,
                    generation_run=run,
                    blueprint=blueprint_model,
                    parent_id=item.parent_id,
                    source_version_id=run.source_version_id,
                    source_section_id=item.source_section_id,
                    kind=item.kind,
                    position=item.position,
                    title=item.title,
                    description=item.description,
                )
                item_models[item.id] = item_model
            for item in blueprint.items:
                GenerationSourceEdge.objects.create(
                    id=_stable_id("generation-source-edge", run.id, "blueprint_item", item.id),
                    tenant_id=tenant_id,
                    generation_run=run,
                    source_version_id=run.source_version_id,
                    source_section_id=item.source_section_id,
                    edge_kind="blueprint_item",
                    blueprint_item=item_models[item.id],
                )
            run.status = "blueprint_review"
            run.blueprint_content_sha256 = blueprint.content_sha256
            run.checkpoint = "blueprint_review"
            run.reason_code = None
            run.lease_owner = None
            run.lease_expires_at = None
            run.heartbeat_at = now
            run.row_version += 1
            run.save()
            attempt.outcome = "completed"
            attempt.output_manifest_sha256 = blueprint.content_sha256
            attempt.checkpoint = "blueprint_review"
            attempt.observation = {"blueprint_item_count": len(blueprint.items)}
            attempt.completed_at = now
            attempt.save()
            self._record_fact(
                actor_id=_WORKER_ACTOR_ID,
                run=run,
                event_type="course_generation.blueprint_ready.v1",
            )
            return run

    def _persist_lessons(
        self,
        *,
        tenant_id: UUID,
        run_id: UUID,
        worker_id: str,
        lessons: tuple[GeneratedLessonDraft, ...],
    ) -> CourseGenerationRun:
        output_manifest_sha256 = _manifest_hash(
            [
                {
                    "id": str(lesson.id),
                    "blueprint_lesson_item_id": str(lesson.blueprint_lesson_item_id),
                    "source_section_id": str(lesson.source_section_id),
                    "content_sha256": lesson.content_sha256,
                }
                for lesson in lessons
            ]
        )
        with transaction.atomic():
            _set_worker_context(tenant_id=tenant_id, run_id=run_id, stage="draft_commit")
            try:
                run = CourseGenerationRun.objects.select_for_update().get(
                    tenant_id=tenant_id, id=run_id
                )
                attempt = CourseGenerationAttempt.objects.select_for_update().get(
                    tenant_id=tenant_id,
                    generation_run_id=run.id,
                    attempt_number=run.attempt_count,
                    outcome="running",
                )
            except (
                CourseGenerationAttempt.DoesNotExist,
                CourseGenerationRun.DoesNotExist,
            ) as error:
                raise CourseGenerationError("GENERATION_STATE_CONFLICT") from error
            now = timezone.now()
            if (
                run.status != "generating"
                or run.lease_owner != worker_id.strip()
                or run.lease_expires_at is None
                or run.lease_expires_at <= now
            ):
                raise CourseGenerationError("GENERATION_LEASE_CONFLICT")
            if not self._active_generate_authorization(run):
                raise _RightsBlockedError
            item_models = {
                item.id: item
                for item in CourseBlueprintItem.objects.filter(
                    tenant_id=tenant_id,
                    generation_run_id=run.id,
                    kind="lesson",
                )
            }
            for lesson in lessons:
                artifact = GeneratedLessonArtifact.objects.create(
                    id=lesson.id,
                    tenant_id=tenant_id,
                    generation_run=run,
                    blueprint_item=item_models[lesson.blueprint_lesson_item_id],
                    source_version_id=run.source_version_id,
                    source_section_id=lesson.source_section_id,
                    revision=1,
                    schema_version=lesson.schema_version,
                    title=lesson.title,
                    document=lesson.document,
                    content_sha256=lesson.content_sha256,
                )
                GenerationSourceEdge.objects.create(
                    id=_stable_id(
                        "generation-source-edge", run.id, "generated_lesson", artifact.id
                    ),
                    tenant_id=tenant_id,
                    generation_run=run,
                    source_version_id=run.source_version_id,
                    source_section_id=lesson.source_section_id,
                    edge_kind="generated_lesson",
                    generated_artifact=artifact,
                )
            run.status = "review_ready"
            run.output_manifest_sha256 = output_manifest_sha256
            run.checkpoint = "review_ready"
            run.reason_code = None
            run.lease_owner = None
            run.lease_expires_at = None
            run.heartbeat_at = now
            run.row_version += 1
            run.save()
            attempt.outcome = "completed"
            attempt.output_manifest_sha256 = output_manifest_sha256
            attempt.checkpoint = "review_ready"
            attempt.observation = {"generated_lesson_count": len(lessons)}
            attempt.completed_at = now
            attempt.save()
            self._record_fact(
                actor_id=_WORKER_ACTOR_ID,
                run=run,
                event_type="course_generation.review_ready.v1",
            )
            return run

    def run_generation(
        self,
        *,
        tenant_id: UUID,
        run_id: UUID,
        worker_id: str,
    ) -> GenerationWorkerResult:
        run, _attempt, claimed = self._claim(
            tenant_id=tenant_id, run_id=run_id, worker_id=worker_id
        )
        if not claimed:
            return GenerationWorkerResult(run=self._record(run), claimed=False)
        try:
            with transaction.atomic():
                _set_worker_context(tenant_id=tenant_id, run_id=run_id, stage="source_read")
                current = CourseGenerationRun.objects.get(tenant_id=tenant_id, id=run_id)
                if not self._active_generate_authorization(current):
                    raise _RightsBlockedError
                document = SourceDocument.objects.get(
                    tenant_id=tenant_id,
                    id=current.source_document_id,
                    current_version_id=current.source_version_id,
                )
                sections = self._load_source_sections(
                    tenant_id=tenant_id,
                    source_document_id=current.source_document_id,
                    source_version_id=current.source_version_id,
                    ingestion_run_id=current.ingestion_run_id,
                )
                blueprint_model = (
                    CourseBlueprint.objects.filter(
                        tenant_id=tenant_id,
                        generation_run_id=current.id,
                        status="approved",
                    )
                    .order_by("-revision")
                    .first()
                )
                blueprint = (
                    None if blueprint_model is None else self._blueprint_record(blueprint_model)
                )
                source_title = document.display_name
                intent = self._intent_from_run(current)
            if run.status == "planning":
                planned = self._adapter.plan(
                    run_id=run.id,
                    source_title=source_title,
                    intent=intent,
                    sections=sections,
                )
                self._validate_blueprint(run=run, blueprint=planned, sections=sections)
                persisted = self._persist_blueprint(
                    tenant_id=tenant_id,
                    run_id=run_id,
                    worker_id=worker_id,
                    blueprint=planned,
                )
            else:
                if blueprint is None:
                    raise CourseGenerationError("GENERATION_STATE_CONFLICT")
                lessons = self._adapter.generate(
                    run_id=run.id,
                    blueprint=blueprint,
                    sections=sections,
                )
                self._validate_lessons(blueprint=blueprint, lessons=lessons, sections=sections)
                persisted = self._persist_lessons(
                    tenant_id=tenant_id,
                    run_id=run_id,
                    worker_id=worker_id,
                    lessons=lessons,
                )
            return GenerationWorkerResult(run=self._record(persisted), claimed=True)
        except _RightsBlockedError:
            failed = self._finish_failure(
                tenant_id=tenant_id,
                run_id=run_id,
                worker_id=worker_id,
                reason_code="GENERATION_RIGHTS_INACTIVE",
                retryable=False,
                rights_blocked=True,
            )
            return GenerationWorkerResult(run=self._record(failed), claimed=True)
        except CourseGenerationError as error:
            failed = self._finish_failure(
                tenant_id=tenant_id,
                run_id=run_id,
                worker_id=worker_id,
                reason_code=error.code,
                retryable=error.code in _RETRYABLE_REASON_CODES,
            )
            return GenerationWorkerResult(run=self._record(failed), claimed=True)
        except ValueError as error:
            reason = (
                str(error) if str(error).startswith("GENERATION_") else "GENERATION_OUTPUT_INVALID"
            )
            failed = self._finish_failure(
                tenant_id=tenant_id,
                run_id=run_id,
                worker_id=worker_id,
                reason_code=reason,
                retryable=False,
            )
            return GenerationWorkerResult(run=self._record(failed), claimed=True)
        except Exception:
            failed = self._finish_failure(
                tenant_id=tenant_id,
                run_id=run_id,
                worker_id=worker_id,
                reason_code="GENERATION_ADAPTER_FAILED",
                retryable=True,
            )
            return GenerationWorkerResult(run=self._record(failed), claimed=True)

    def approve_blueprint(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        run_id: UUID,
        command: ApproveBlueprintCommand,
        idempotency_key: str,
    ) -> GenerationRunRecord:
        request = {
            "run_id": run_id,
            "expected_run_row_version": command.expected_run_row_version,
            "blueprint_id": command.blueprint_id,
            "blueprint_revision": command.blueprint_revision,
            "expected_blueprint_content_sha256": command.expected_blueprint_content_sha256,
        }
        with transaction.atomic():
            self._authorize(
                actor_id=actor_id,
                tenant_id=tenant_id,
                permission=PERMISSION_BLUEPRINT_REVIEW,
            )
            reservation, replay = self._reserve_idempotency(
                actor_id=actor_id,
                tenant_id=tenant_id,
                key=idempotency_key,
                request=request,
                operation="course_generation.blueprints.approve",
            )
            if replay is not None:
                try:
                    replayed = CourseGenerationRun.objects.get(
                        tenant_id=tenant_id,
                        id=UUID(str(replay["resource_id"])),
                    )
                except (KeyError, ValueError, CourseGenerationRun.DoesNotExist) as error:
                    raise CourseGenerationError("SERVICE_CONTRACT_ERROR") from error
                return self._record(replayed)
            try:
                run = CourseGenerationRun.objects.select_for_update().get(
                    tenant_id=tenant_id, id=run_id
                )
                blueprint = CourseBlueprint.objects.select_for_update().get(
                    tenant_id=tenant_id,
                    generation_run_id=run.id,
                    id=command.blueprint_id,
                    revision=command.blueprint_revision,
                )
            except (
                CourseBlueprint.DoesNotExist,
                CourseGenerationRun.DoesNotExist,
            ) as error:
                raise CourseGenerationError("GENERATION_RESOURCE_NOT_FOUND") from error
            if (
                run.status != "blueprint_review"
                or blueprint.status != "reviewable"
                or run.row_version != command.expected_run_row_version
                or run.blueprint_content_sha256 != command.expected_blueprint_content_sha256
                or blueprint.content_sha256 != command.expected_blueprint_content_sha256
            ):
                raise CourseGenerationError("GENERATION_VERSION_CONFLICT")
            now = timezone.now()
            BlueprintReviewDecision.objects.create(
                tenant_id=tenant_id,
                generation_run=run,
                blueprint=blueprint,
                decided_by_actor_id=actor_id,
                decision="approve",
                reviewed_content_sha256=command.expected_blueprint_content_sha256,
                decided_at=now,
            )
            blueprint.status = "approved"
            blueprint.save(update_fields=("status",))
            run.status = "generation_queued"
            run.checkpoint = "blueprint_approved"
            run.reason_code = None
            run.row_version += 1
            run.save(
                update_fields=(
                    "status",
                    "checkpoint",
                    "reason_code",
                    "row_version",
                    "updated_at",
                )
            )
            self._record_review_audit(
                actor_id=actor_id,
                run=run,
                event_type="course_generation.blueprint_approved.v1",
                reviewed_content_sha256=command.expected_blueprint_content_sha256,
            )
            self._complete_run_idempotency(reservation, run=run)
            return self._record(run)

    def reject_generation(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        run_id: UUID,
        command: RejectGenerationCommand,
        idempotency_key: str,
    ) -> GenerationRunRecord:
        request = {
            "run_id": run_id,
            "expected_run_row_version": command.expected_run_row_version,
            "expected_review_content_sha256": command.expected_review_content_sha256,
            "reason_code": command.reason_code,
        }
        with transaction.atomic():
            self._authorize(
                actor_id=actor_id,
                tenant_id=tenant_id,
                permission=PERMISSION_BLUEPRINT_REVIEW,
            )
            reservation, replay = self._reserve_idempotency(
                actor_id=actor_id,
                tenant_id=tenant_id,
                key=idempotency_key,
                request=request,
                operation="course_generation.runs.reject",
            )
            if replay is not None:
                try:
                    replayed = CourseGenerationRun.objects.get(
                        tenant_id=tenant_id,
                        id=UUID(str(replay["resource_id"])),
                    )
                except (KeyError, ValueError, CourseGenerationRun.DoesNotExist) as error:
                    raise CourseGenerationError("SERVICE_CONTRACT_ERROR") from error
                return self._record(replayed)
            try:
                run = CourseGenerationRun.objects.select_for_update().get(
                    tenant_id=tenant_id, id=run_id
                )
            except CourseGenerationRun.DoesNotExist as error:
                raise CourseGenerationError("GENERATION_RESOURCE_NOT_FOUND") from error
            if run.row_version != command.expected_run_row_version:
                raise CourseGenerationError("GENERATION_VERSION_CONFLICT")
            now = timezone.now()
            if run.status == "blueprint_review":
                try:
                    blueprint = CourseBlueprint.objects.select_for_update().get(
                        tenant_id=tenant_id,
                        generation_run_id=run.id,
                        status="reviewable",
                    )
                except CourseBlueprint.DoesNotExist as error:
                    raise CourseGenerationError("GENERATION_STATE_CONFLICT") from error
                if (
                    blueprint.content_sha256 != command.expected_review_content_sha256
                    or run.blueprint_content_sha256 != command.expected_review_content_sha256
                ):
                    raise CourseGenerationError("GENERATION_VERSION_CONFLICT")
                BlueprintReviewDecision.objects.create(
                    tenant_id=tenant_id,
                    generation_run=run,
                    blueprint=blueprint,
                    decided_by_actor_id=actor_id,
                    decision="reject",
                    reviewed_content_sha256=command.expected_review_content_sha256,
                    reason_code=command.reason_code,
                    decided_at=now,
                )
                blueprint.status = "rejected"
                blueprint.save(update_fields=("status",))
            elif run.status == "review_ready":
                if run.output_manifest_sha256 != command.expected_review_content_sha256:
                    raise CourseGenerationError("GENERATION_VERSION_CONFLICT")
                CourseGenerationRejection.objects.create(
                    tenant_id=tenant_id,
                    generation_run=run,
                    rejected_by_actor_id=actor_id,
                    reviewed_output_sha256=command.expected_review_content_sha256,
                    reason_code=command.reason_code,
                    rejected_at=now,
                )
            else:
                raise CourseGenerationError("GENERATION_STATE_CONFLICT")
            run.status = "rejected"
            run.reason_code = command.reason_code
            run.checkpoint = "human_rejected"
            run.row_version += 1
            run.save(
                update_fields=(
                    "status",
                    "reason_code",
                    "checkpoint",
                    "row_version",
                    "updated_at",
                )
            )
            self._record_fact(
                actor_id=actor_id,
                run=run,
                event_type="course_generation.rejected.v1",
            )
            self._complete_run_idempotency(reservation, run=run)
            return self._record(run)

    @staticmethod
    def _canonicalization_record(
        canonicalization: GenerationCanonicalization,
    ) -> CanonicalizationRecord:
        return CanonicalizationRecord(
            id=canonicalization.id,
            tenant_id=canonicalization.tenant_id,
            generation_run_id=canonicalization.generation_run_id,
            course_id=canonicalization.course_id,
            course_version_id=canonicalization.course_version_id,
            reviewed_output_sha256=canonicalization.reviewed_output_sha256,
            canonical_content_sha256=canonicalization.canonical_content_sha256,
            canonicalization_sha256=canonicalization.canonicalization_sha256,
            canonicalized_by_actor_id=canonicalization.canonicalized_by_actor_id,
            created_at=canonicalization.created_at,
        )

    @staticmethod
    def _lock_canonicalization_scope(
        *,
        tenant_id: UUID,
        run_id: UUID,
        expected_run_row_version: int,
        expected_output_manifest_sha256: str,
    ) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT app.lock_generation_canonicalization_scope(%s, %s, %s, %s)
                """,
                [
                    str(tenant_id),
                    str(run_id),
                    expected_run_row_version,
                    expected_output_manifest_sha256,
                ],
            )
            row = cursor.fetchone()
        return row is not None and row[0] is True

    @staticmethod
    def _translate_course_error(error: CourseLifecycleError) -> CourseGenerationError:
        if error.code in {"COURSE_PERMISSION_DENIED", "TENANT_ACCESS_INACTIVE"}:
            return CourseGenerationError("GENERATION_PERMISSION_DENIED")
        if error.code == "COURSE_VALIDATION_FAILED":
            return CourseGenerationError(
                "GENERATION_VALIDATION_FAILED",
                field_errors=tuple(
                    FieldError(f"course.{item.path}", item.code) for item in error.field_errors
                ),
            )
        if error.code == "IDEMPOTENCY_CONFLICT":
            return CourseGenerationError("IDEMPOTENCY_CONFLICT")
        if error.code == "VERSION_CONFLICT":
            return CourseGenerationError("GENERATION_SLUG_CONFLICT")
        if error.code == "RESOURCE_NOT_FOUND":
            return CourseGenerationError("GENERATION_RESOURCE_NOT_FOUND")
        return CourseGenerationError("SERVICE_CONTRACT_ERROR")

    @staticmethod
    def _record_canonicalization_fact(
        *,
        actor_id: UUID,
        run: CourseGenerationRun,
        canonicalization: GenerationCanonicalization,
    ) -> None:
        request_id = uuid.uuid4()
        now = timezone.now()
        payload: dict[str, JsonValue] = {
            "course_generation_run_id": str(run.id),
            "course_generation_canonicalization_id": str(canonicalization.id),
            "course_id": str(canonicalization.course_id),
            "course_version_id": str(canonicalization.course_version_id),
            "reviewed_output_sha256": canonicalization.reviewed_output_sha256,
            "canonical_content_sha256": canonicalization.canonical_content_sha256,
            "canonicalization_sha256": canonicalization.canonicalization_sha256,
            "status": run.status,
            "row_version": run.row_version,
        }
        AuditFact.objects.create(
            tenant_id=run.tenant_id,
            event_type="course_generation.canonicalized.v1",
            actor_id=actor_id,
            subject_type="course_generation_run",
            subject_id=run.id,
            request_id=request_id,
            payload=payload,
        )
        OutboxFact.objects.create(
            tenant_id=run.tenant_id,
            event_type="course_generation.canonicalized.v1",
            aggregate_type="course_generation_run",
            aggregate_id=run.id,
            actor_id=actor_id,
            request_id=request_id,
            payload={
                "event_version": 1,
                "producer": "course_generation",
                "recorded_at": now.isoformat(),
                "privacy_class": "internal",
                **payload,
            },
        )

    def canonicalize_generation(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        run_id: UUID,
        command: CanonicalizeGenerationCommand,
        idempotency_key: str,
    ) -> CanonicalizationRecord:
        errors: list[FieldError] = []
        if command.expected_run_row_version < 1:
            errors.append(FieldError("expected_run_row_version", "out_of_range"))
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", command.expected_output_manifest_sha256):
            errors.append(FieldError("expected_output_manifest_sha256", "invalid"))
        if not _SLUG.fullmatch(command.course_slug) or len(command.course_slug) > 63:
            errors.append(FieldError("course_slug", "invalid_slug"))
        if errors:
            raise CourseGenerationError("GENERATION_VALIDATION_FAILED", field_errors=tuple(errors))
        request = {
            "run_id": run_id,
            "expected_run_row_version": command.expected_run_row_version,
            "expected_output_manifest_sha256": command.expected_output_manifest_sha256,
            "course_slug": command.course_slug,
        }
        with transaction.atomic():
            self._authorize(
                actor_id=actor_id,
                tenant_id=tenant_id,
                permission=PERMISSION_DRAFT_CANONICALIZE,
            )
            reservation, replay = self._reserve_idempotency(
                actor_id=actor_id,
                tenant_id=tenant_id,
                key=idempotency_key,
                request=request,
                operation=PERMISSION_DRAFT_CANONICALIZE,
            )
            if replay is not None:
                try:
                    canonicalization = GenerationCanonicalization.objects.get(
                        tenant_id=tenant_id,
                        id=UUID(str(replay["canonicalization_id"])),
                        generation_run_id=run_id,
                    )
                except (
                    KeyError,
                    ValueError,
                    GenerationCanonicalization.DoesNotExist,
                ) as error:
                    raise CourseGenerationError("SERVICE_CONTRACT_ERROR") from error
                return self._canonicalization_record(canonicalization)
            if self._course_drafts is None:
                raise CourseGenerationError("SERVICE_CONTRACT_ERROR")
            try:
                run = CourseGenerationRun.objects.select_for_update().get(
                    tenant_id=tenant_id,
                    id=run_id,
                )
            except CourseGenerationRun.DoesNotExist as error:
                raise CourseGenerationError("GENERATION_RESOURCE_NOT_FOUND") from error
            if (
                run.status != "review_ready"
                or run.row_version != command.expected_run_row_version
                or run.output_manifest_sha256 != command.expected_output_manifest_sha256
            ):
                raise CourseGenerationError("GENERATION_OUTPUT_HASH_MISMATCH")
            if not self._lock_canonicalization_scope(
                tenant_id=tenant_id,
                run_id=run_id,
                expected_run_row_version=command.expected_run_row_version,
                expected_output_manifest_sha256=command.expected_output_manifest_sha256,
            ):
                raise CourseGenerationError("GENERATION_STATE_CONFLICT")
            try:
                SourceDocument.objects.get(
                    tenant_id=tenant_id,
                    id=run.source_document_id,
                    current_version_id=run.source_version_id,
                )
                SourceVersion.objects.get(
                    tenant_id=tenant_id,
                    source_document_id=run.source_document_id,
                    id=run.source_version_id,
                    admission_status="admitted",
                )
                DocumentIngestionRun.objects.get(
                    tenant_id=tenant_id,
                    source_document_id=run.source_document_id,
                    source_version_id=run.source_version_id,
                    id=run.ingestion_run_id,
                    status="ready_for_generation",
                )
                authorization = SourceUseAuthorization.objects.get(
                    tenant_id=tenant_id,
                    source_document_id=run.source_document_id,
                    source_version_id=run.source_version_id,
                    id=run.generate_authorization_id,
                    operation="generate",
                )
                blueprint = CourseBlueprint.objects.get(
                    tenant_id=tenant_id,
                    generation_run_id=run.id,
                    status="approved",
                )
            except (
                CourseBlueprint.DoesNotExist,
                DocumentIngestionRun.DoesNotExist,
                SourceDocument.DoesNotExist,
                SourceUseAuthorization.DoesNotExist,
                SourceVersion.DoesNotExist,
            ) as error:
                raise CourseGenerationError("GENERATION_SOURCE_NOT_READY") from error
            if not self._authorization_is_active(authorization):
                raise CourseGenerationError("GENERATION_RIGHTS_INACTIVE")

            modules = tuple(
                CourseBlueprintItem.objects.filter(
                    tenant_id=tenant_id,
                    generation_run_id=run.id,
                    blueprint_id=blueprint.id,
                    kind="module",
                ).order_by("position", "id")
            )
            lesson_items = tuple(
                CourseBlueprintItem.objects.filter(
                    tenant_id=tenant_id,
                    generation_run_id=run.id,
                    blueprint_id=blueprint.id,
                    kind="lesson",
                ).order_by("parent_id", "position", "id")
            )
            artifacts = tuple(
                GeneratedLessonArtifact.objects.filter(
                    tenant_id=tenant_id,
                    generation_run_id=run.id,
                    revision=1,
                ).order_by("blueprint_item__position", "id")
            )
            generated_edges = tuple(
                GenerationSourceEdge.objects.filter(
                    tenant_id=tenant_id,
                    generation_run_id=run.id,
                    edge_kind="generated_lesson",
                ).order_by("generated_artifact_id", "id")
            )
            lessons_by_parent: dict[UUID, CourseBlueprintItem] = {}
            for item in lesson_items:
                if item.parent_id is None or item.parent_id in lessons_by_parent:
                    raise CourseGenerationError("GENERATION_PROVENANCE_INVALID")
                lessons_by_parent[item.parent_id] = item
            artifacts_by_item = {artifact.blueprint_item_id: artifact for artifact in artifacts}
            edges_by_artifact = {
                edge.generated_artifact_id: edge
                for edge in generated_edges
                if edge.generated_artifact_id is not None
            }
            if (
                not modules
                or [module.position for module in modules] != list(range(1, len(modules) + 1))
                or len(lesson_items) != len(modules)
                or len(artifacts) != len(modules)
                or len(artifacts_by_item) != len(artifacts)
                or len(generated_edges) != len(artifacts)
                or len(edges_by_artifact) != len(artifacts)
            ):
                raise CourseGenerationError("GENERATION_PROVENANCE_INVALID")

            ordered_artifacts: list[GeneratedLessonArtifact] = []
            section_inputs: list[CurriculumSectionInput] = []
            for module in modules:
                lesson_item = lessons_by_parent.get(module.id)
                artifact = None if lesson_item is None else artifacts_by_item.get(lesson_item.id)
                edge = None if artifact is None else edges_by_artifact.get(artifact.id)
                if (
                    lesson_item is None
                    or artifact is None
                    or edge is None
                    or module.source_version_id != run.source_version_id
                    or lesson_item.source_version_id != run.source_version_id
                    or artifact.source_version_id != run.source_version_id
                    or edge.source_version_id != run.source_version_id
                    or module.source_section_id != lesson_item.source_section_id
                    or lesson_item.source_section_id != artifact.source_section_id
                    or artifact.source_section_id != edge.source_section_id
                ):
                    raise CourseGenerationError("GENERATION_PROVENANCE_INVALID")
                document_value = _as_json_object(artifact.document)
                try:
                    validate_rich_text_document(document_value)
                except CourseLifecycleError as error:
                    raise CourseGenerationError("GENERATION_SCHEMA_INVALID") from error
                ordered_artifacts.append(artifact)
                section_inputs.append(
                    CurriculumSectionInput(
                        title=module.title,
                        position=module.position,
                        lessons=(
                            LessonInput(
                                title=artifact.title,
                                position=1,
                                is_required=True,
                                content_blocks=(
                                    ContentBlockInput(
                                        kind="rich_text",
                                        position=1,
                                        document=document_value,
                                    ),
                                ),
                            ),
                        ),
                    )
                )

            try:
                snapshot = self._course_drafts.create_ai_assisted_draft(
                    actor_id=actor_id,
                    tenant_id=tenant_id,
                    command=CreateAiAssistedDraftCommand(
                        slug=command.course_slug,
                        primary_locale=run.locale,
                        title=blueprint.title,
                        description=blueprint.description,
                        sections=tuple(section_inputs),
                    ),
                    idempotency_key=f"canonical-course-{_request_hash(idempotency_key)}",
                )
            except CourseLifecycleError as error:
                raise self._translate_course_error(error) from error
            if (
                snapshot.course.tenant_id != tenant_id
                or snapshot.course.current_published_version_id is not None
                or snapshot.version.tenant_id != tenant_id
                or snapshot.version.course_id != snapshot.course.id
                or snapshot.version.status is not CourseStatus.DRAFT
                or snapshot.version.origin_type is not OriginType.AI_ASSISTED
                or snapshot.version.submitted_hash is not None
                or snapshot.version.approved_hash is not None
                or len(snapshot.sections) != len(ordered_artifacts)
            ):
                raise CourseGenerationError("SERVICE_CONTRACT_ERROR")
            mappings: list[dict[str, object]] = []
            canonical_rows: list[
                tuple[GeneratedLessonArtifact, CurriculumSection, Lesson, RichTextBlock]
            ] = []
            for artifact, section in zip(ordered_artifacts, snapshot.sections, strict=True):
                if len(section.lessons) != 1 or len(section.lessons[0].content_blocks) != 1:
                    raise CourseGenerationError("SERVICE_CONTRACT_ERROR")
                lesson = section.lessons[0]
                block = lesson.content_blocks[0]
                if block.document != artifact.document:
                    raise CourseGenerationError("SERVICE_CONTRACT_ERROR")
                mappings.append(
                    {
                        "generated_artifact_id": str(artifact.id),
                        "source_version_id": str(artifact.source_version_id),
                        "source_section_id": str(artifact.source_section_id),
                        "course_id": str(snapshot.course.id),
                        "course_version_id": str(snapshot.version.id),
                        "curriculum_section_id": str(section.id),
                        "lesson_id": str(lesson.id),
                        "content_block_id": str(block.id),
                        "artifact_content_sha256": artifact.content_sha256,
                    }
                )
                canonical_rows.append((artifact, section, lesson, block))
            canonicalization_id = _stable_id(
                "generation-canonicalization",
                run.id,
                snapshot.course.id,
                snapshot.version.id,
            )
            canonicalization_sha256 = _manifest_hash(
                {
                    "id": str(canonicalization_id),
                    "generation_run_id": str(run.id),
                    "reviewed_output_sha256": command.expected_output_manifest_sha256,
                    "course_id": str(snapshot.course.id),
                    "course_version_id": str(snapshot.version.id),
                    "canonical_content_sha256": snapshot.version.content_hash,
                    "mappings": mappings,
                }
            )
            canonicalization = GenerationCanonicalization.objects.create(
                id=canonicalization_id,
                tenant_id=tenant_id,
                generation_run=run,
                course_id=snapshot.course.id,
                course_version_id=snapshot.version.id,
                canonicalized_by_actor_id=actor_id,
                requested_course_slug=command.course_slug,
                reviewed_output_sha256=command.expected_output_manifest_sha256,
                canonical_content_sha256=snapshot.version.content_hash,
                canonicalization_sha256=canonicalization_sha256,
            )
            for artifact, section, lesson, block in canonical_rows:
                CanonicalizationSourceEdge.objects.create(
                    id=_stable_id("canonicalization-source-edge", canonicalization.id, artifact.id),
                    tenant_id=tenant_id,
                    canonicalization=canonicalization,
                    generation_run=run,
                    generated_artifact=artifact,
                    source_version_id=artifact.source_version_id,
                    source_section_id=artifact.source_section_id,
                    course_id=snapshot.course.id,
                    course_version_id=snapshot.version.id,
                    curriculum_section_id=section.id,
                    lesson_id=lesson.id,
                    content_block_id=block.id,
                )
            run.status = "canonicalized"
            run.checkpoint = "canonicalized"
            run.reason_code = None
            run.row_version += 1
            run.save(
                update_fields=(
                    "status",
                    "checkpoint",
                    "reason_code",
                    "row_version",
                    "updated_at",
                )
            )
            self._record_canonicalization_fact(
                actor_id=actor_id,
                run=run,
                canonicalization=canonicalization,
            )
            self._complete_idempotency(
                reservation,
                payload={
                    "canonicalization_id": str(canonicalization.id),
                    "resource_id": str(run.id),
                    "course_id": str(canonicalization.course_id),
                    "course_version_id": str(canonicalization.course_version_id),
                },
            )
            return self._canonicalization_record(canonicalization)
