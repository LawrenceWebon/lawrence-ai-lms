from __future__ import annotations

import ast
import copy
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from lms.adapters.admin.courses import (
    COURSE_LIFECYCLE_READONLY_FIELDS,
    AdminActorContext,
    CourseAdminActions,
)
from lms.api.schemas.courses import (
    CourseAdministrationError,
    CreateCourseV1,
    CreateSuccessorDraftV1,
    ReplaceCurriculumV1,
    TransitionCourseVersionV1,
    UpdateCourseVersionV1,
)
from tests.contract_fakes.f002_course_administration import (
    ACTOR_ID,
    ALPHA_TENANT_ID,
    BETA_TENANT_ID,
    COURSE_ID,
    IDEMPOTENCY_KEY,
    VERSION_ID,
    RecordingCourseAdministrationServiceFake,
    load_lifecycle_examples,
)


def actor_context(*, tenant_id: UUID | None = ALPHA_TENANT_ID) -> AdminActorContext:
    return AdminActorContext(actor_id=ACTOR_ID, tenant_id=tenant_id)


def test_admin_actions_delegate_every_operation_to_the_shared_structural_service() -> None:
    examples = load_lifecycle_examples()
    service = RecordingCourseAdministrationServiceFake()
    actions = CourseAdminActions(service=service)
    context = actor_context()

    created = actions.create_course(
        context=context,
        request=CreateCourseV1.model_validate(examples["CreateCourseV1"]),
        idempotency_key=IDEMPOTENCY_KEY,
    )
    fetched = actions.get_course_version(
        context=context,
        course_id=COURSE_ID,
        version_id=VERSION_ID,
    )
    history = actions.list_course_versions(
        context=context,
        course_id=COURSE_ID,
        cursor="synthetic-opaque-cursor",
        limit=25,
    )
    updated = actions.update_version(
        context=context,
        course_id=COURSE_ID,
        version_id=VERSION_ID,
        request=UpdateCourseVersionV1.model_validate(examples["UpdateCourseVersionV1"]),
    )
    replaced = actions.replace_curriculum(
        context=context,
        course_id=COURSE_ID,
        version_id=VERSION_ID,
        request=ReplaceCurriculumV1.model_validate(examples["ReplaceCurriculumV1"]),
    )
    transitioned = actions.transition_version(
        context=context,
        course_id=COURSE_ID,
        version_id=VERSION_ID,
        request=TransitionCourseVersionV1.model_validate(examples["TransitionCourseVersionV1"]),
        idempotency_key=IDEMPOTENCY_KEY,
    )
    successor = actions.create_successor_draft(
        context=context,
        course_id=COURSE_ID,
        source_version_id=VERSION_ID,
        request=CreateSuccessorDraftV1.model_validate(examples["CreateSuccessorDraftV1"]),
        idempotency_key=IDEMPOTENCY_KEY,
    )

    assert created == fetched == updated == replaced == transitioned
    assert history.course_id == COURSE_ID
    assert successor.source_version_id == VERSION_ID
    assert [call.operation for call in service.calls] == [
        "create_course",
        "get_course_version",
        "list_course_versions",
        "update_version",
        "replace_curriculum",
        "transition_version",
        "create_successor_draft",
    ]
    assert all(call.actor_id == ACTOR_ID for call in service.calls)
    assert all(call.tenant_id == ALPHA_TENANT_ID for call in service.calls)


@pytest.mark.parametrize(
    "operation",
    [
        "create_course",
        "get_course_version",
        "list_course_versions",
        "update_version",
        "replace_curriculum",
        "transition_version",
        "create_successor_draft",
    ],
)
def test_all_admin_operations_require_explicit_trusted_tenant_context(operation: str) -> None:
    examples = load_lifecycle_examples()
    service = RecordingCourseAdministrationServiceFake()
    actions = CourseAdminActions(service=service)
    context = AdminActorContext(actor_id=ACTOR_ID, tenant_id=None)

    with pytest.raises(CourseAdministrationError) as caught:
        if operation == "create_course":
            actions.create_course(
                context=context,
                request=CreateCourseV1.model_validate(examples["CreateCourseV1"]),
                idempotency_key=IDEMPOTENCY_KEY,
            )
        elif operation == "get_course_version":
            actions.get_course_version(context=context, course_id=COURSE_ID, version_id=VERSION_ID)
        elif operation == "list_course_versions":
            actions.list_course_versions(
                context=context, course_id=COURSE_ID, cursor=None, limit=50
            )
        elif operation == "update_version":
            actions.update_version(
                context=context,
                course_id=COURSE_ID,
                version_id=VERSION_ID,
                request=UpdateCourseVersionV1.model_validate(examples["UpdateCourseVersionV1"]),
            )
        elif operation == "replace_curriculum":
            actions.replace_curriculum(
                context=context,
                course_id=COURSE_ID,
                version_id=VERSION_ID,
                request=ReplaceCurriculumV1.model_validate(examples["ReplaceCurriculumV1"]),
            )
        elif operation == "transition_version":
            actions.transition_version(
                context=context,
                course_id=COURSE_ID,
                version_id=VERSION_ID,
                request=TransitionCourseVersionV1.model_validate(
                    examples["TransitionCourseVersionV1"]
                ),
                idempotency_key=IDEMPOTENCY_KEY,
            )
        else:
            actions.create_successor_draft(
                context=context,
                course_id=COURSE_ID,
                source_version_id=VERSION_ID,
                request=CreateSuccessorDraftV1.model_validate(examples["CreateSuccessorDraftV1"]),
                idempotency_key=IDEMPOTENCY_KEY,
            )

    assert caught.value.code == "TENANT_CONTEXT_REQUIRED"
    assert service.calls == []


def test_admin_does_not_translate_or_weaken_service_authorization() -> None:
    service = RecordingCourseAdministrationServiceFake()
    service.problem_by_operation["get_course_version"] = CourseAdministrationError(
        code="RESOURCE_NOT_FOUND",
        status=404,
        title="Resource unavailable",
        detail="The resource is unavailable.",
    )
    actions = CourseAdminActions(service=service)

    with pytest.raises(CourseAdministrationError) as caught:
        actions.get_course_version(
            context=actor_context(tenant_id=BETA_TENANT_ID),
            course_id=COURSE_ID,
            version_id=VERSION_ID,
        )

    assert caught.value.code == "RESOURCE_NOT_FOUND"


@pytest.mark.parametrize("invalid_key", ["short", "x" * 129])
def test_admin_rejects_invalid_idempotency_keys_before_service_call(
    invalid_key: str,
) -> None:
    examples = load_lifecycle_examples()
    service = RecordingCourseAdministrationServiceFake()
    actions = CourseAdminActions(service=service)

    with pytest.raises(CourseAdministrationError) as caught:
        actions.create_course(
            context=actor_context(),
            request=CreateCourseV1.model_validate(examples["CreateCourseV1"]),
            idempotency_key=invalid_key,
        )

    assert caught.value.code == "COURSE_VALIDATION_FAILED"
    assert service.calls == []


@pytest.mark.parametrize(
    ("cursor", "limit"),
    [(None, 0), (None, 101), ("", 50), ("x" * 2049, 50)],
)
def test_admin_rejects_invalid_history_bounds_before_service_call(
    cursor: str | None,
    limit: int,
) -> None:
    service = RecordingCourseAdministrationServiceFake()
    actions = CourseAdminActions(service=service)

    with pytest.raises(CourseAdministrationError) as caught:
        actions.list_course_versions(
            context=actor_context(),
            course_id=COURSE_ID,
            cursor=cursor,
            limit=limit,
        )

    assert caught.value.code == "COURSE_VALIDATION_FAILED"
    assert service.calls == []


def test_admin_validates_service_responses_against_the_frozen_contract() -> None:
    service = RecordingCourseAdministrationServiceFake()
    invalid = copy.deepcopy(service.snapshot)
    assert isinstance(invalid, dict)
    invalid["version"]["tenant_id"] = str(BETA_TENANT_ID)
    service.response_by_operation["get_course_version"] = invalid
    actions = CourseAdminActions(service=service)

    with pytest.raises(ValidationError):
        actions.get_course_version(
            context=actor_context(),
            course_id=COURSE_ID,
            version_id=VERSION_ID,
        )


def test_lifecycle_managed_fields_are_read_only_in_admin() -> None:
    assert {
        "tenant_id",
        "reviewer_policy",
        "current_published_version_id",
        "predecessor_version_id",
        "version_number",
        "status",
        "origin_type",
        "content_hash",
        "submitted_hash",
        "approved_hash",
        "row_version",
        "latest_review",
    } <= COURSE_LIFECYCLE_READONLY_FIELDS


def test_admin_adapter_has_no_orm_import_or_generic_write_escape_hatch() -> None:
    source_path = Path("backend/src/lms/adapters/admin/courses.py")
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    method_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}

    assert not any(module.endswith(".models") for module in imports)
    assert not any(module.startswith("lms.modules.courses") for module in imports)
    assert {"objects", "save", "delete"}.isdisjoint(attributes)
    assert {"save_model", "delete_model", "save_form"}.isdisjoint(method_names)
