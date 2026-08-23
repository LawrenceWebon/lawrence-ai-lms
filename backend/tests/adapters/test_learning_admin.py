from __future__ import annotations

import ast
from pathlib import Path

import pytest

from lms.adapters.admin.learning import (
    LEARNING_READONLY_FIELDS,
    LearningAdminActions,
    LearningAdminActorContext,
)
from lms.api.schemas.learning import (
    CreateEnrollmentV1,
    LearningAdministrationError,
    RevokeEnrollmentV1,
)
from tests.contract_fakes.f007_learning import (
    ACTOR_ID,
    ALPHA_TENANT_ID,
    ENROLLMENT_ID,
    IDEMPOTENCY_KEY,
    RecordingLearningServiceFake,
    load_examples,
)


def test_admin_create_and_revoke_delegate_to_the_shared_service() -> None:
    examples = load_examples()
    service = RecordingLearningServiceFake()
    actions = LearningAdminActions(service=service)
    context = LearningAdminActorContext(actor_id=ACTOR_ID, tenant_id=ALPHA_TENANT_ID)

    created = actions.create_enrollment(
        context=context,
        request=CreateEnrollmentV1.model_validate(examples["CreateEnrollmentV1"]),
        idempotency_key=IDEMPOTENCY_KEY,
    )
    revoked = actions.revoke_enrollment(
        context=context,
        enrollment_id=ENROLLMENT_ID,
        request=RevokeEnrollmentV1.model_validate(examples["RevokeEnrollmentV1"]),
        idempotency_key=IDEMPOTENCY_KEY,
    )

    assert created.status == "active"
    assert revoked.status == "revoked"
    assert [call.operation for call in service.calls] == [
        "create_enrollment",
        "revoke_enrollment",
    ]
    assert all(call.actor_id == ACTOR_ID for call in service.calls)
    assert all(call.tenant_id == ALPHA_TENANT_ID for call in service.calls)


def test_admin_requires_explicit_trusted_tenant_context() -> None:
    service = RecordingLearningServiceFake()
    actions = LearningAdminActions(service=service)
    request = CreateEnrollmentV1.model_validate(load_examples()["CreateEnrollmentV1"])

    with pytest.raises(LearningAdministrationError) as caught:
        actions.create_enrollment(
            context=LearningAdminActorContext(actor_id=ACTOR_ID, tenant_id=None),
            request=request,
            idempotency_key=IDEMPOTENCY_KEY,
        )

    assert caught.value.code == "TENANT_CONTEXT_REQUIRED"
    assert service.calls == []


def test_admin_exposes_no_generic_enrollment_or_progress_mutation() -> None:
    assert {
        "course_version_id",
        "status",
        "enrolled_at",
        "revoked_at",
        "row_version",
        "course_progress",
        "lesson_progress",
    } <= LEARNING_READONLY_FIELDS
    source = Path("backend/src/lms/adapters/admin/learning.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    methods = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}

    assert not any(module.endswith(".models") for module in imports)
    assert not any(module.startswith("lms.modules.learning") for module in imports)
    assert {"objects", "save", "delete"}.isdisjoint(attributes)
    assert {"save_model", "delete_model", "save_form"}.isdisjoint(methods)
    assert {"open_lesson", "complete_lesson", "reopen_lesson"}.isdisjoint(methods)
