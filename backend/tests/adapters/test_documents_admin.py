from __future__ import annotations

import ast
from pathlib import Path

import pytest

from lms.adapters.admin.documents import (
    SOURCE_ADMISSION_READONLY_FIELDS,
    AdminActorContext,
    SourceAdmissionAdminActions,
)
from lms.api.schemas.documents import (
    CancelSourceAdmissionV1,
    CreateSourceAdmissionV1,
    ReviewSourceOperationAuthorizationV1,
    ReviewSourceStoreAuthorizationV1,
    SourceAdmissionContractError,
)
from tests.contract_fakes.f003_source_admission import (
    ACTOR_ID,
    ALPHA_TENANT_ID,
    AUTHORIZATION_ID,
    IDEMPOTENCY_KEY,
    INGESTION_RUN_ID,
    OPAQUE_TOKEN,
    SOURCE_DOCUMENT_ID,
    SOURCE_VERSION_ID,
    RecordingSourceAdmissionServiceFake,
    load_source_examples,
)


def context() -> AdminActorContext:
    return AdminActorContext(actor_id=ACTOR_ID, tenant_id=ALPHA_TENANT_ID)


def test_admin_delegates_all_human_and_upload_operations_to_shared_service() -> None:
    examples = load_source_examples()
    service = RecordingSourceAdmissionServiceFake()
    actions = SourceAdmissionAdminActions(service=service)

    actions.create_admission(
        context=context(),
        request=CreateSourceAdmissionV1.model_validate(examples["CreateSourceAdmissionV1"]),
        idempotency_key=IDEMPOTENCY_KEY,
    )
    actions.review_authorization(
        context=context(),
        source_document_id=SOURCE_DOCUMENT_ID,
        source_version_id=SOURCE_VERSION_ID,
        authorization_id=AUTHORIZATION_ID,
        request=ReviewSourceStoreAuthorizationV1.model_validate(
            examples["ReviewSourceStoreAuthorizationV1"]
        ),
        idempotency_key=IDEMPOTENCY_KEY,
    )
    actions.create_upload_intent(
        context=context(),
        source_document_id=SOURCE_DOCUMENT_ID,
        source_version_id=SOURCE_VERSION_ID,
        idempotency_key=IDEMPOTENCY_KEY,
    )
    actions.upload_to_intent(
        opaque_token=OPAQUE_TOKEN,
        content_type="application/pdf",
        body=b"%PDF-1.4\nsynthetic admin fixture\n%%EOF\n",
    )
    actions.get_admission(
        context=context(),
        source_document_id=SOURCE_DOCUMENT_ID,
        source_version_id=SOURCE_VERSION_ID,
    )
    actions.cancel_admission(
        context=context(),
        source_document_id=SOURCE_DOCUMENT_ID,
        source_version_id=SOURCE_VERSION_ID,
        request=CancelSourceAdmissionV1.model_validate(examples["CancelSourceAdmissionV1"]),
        idempotency_key=IDEMPOTENCY_KEY,
    )
    actions.list_operation_authorizations(
        context=context(),
        source_document_id=SOURCE_DOCUMENT_ID,
        source_version_id=SOURCE_VERSION_ID,
    )
    actions.request_operation_authorization(
        context=context(),
        source_document_id=SOURCE_DOCUMENT_ID,
        source_version_id=SOURCE_VERSION_ID,
        operation="extract",
        idempotency_key=IDEMPOTENCY_KEY,
    )
    actions.review_operation_authorization(
        context=context(),
        source_document_id=SOURCE_DOCUMENT_ID,
        source_version_id=SOURCE_VERSION_ID,
        operation="extract",
        request=ReviewSourceOperationAuthorizationV1.model_validate(
            examples["ReviewSourceStoreAuthorizationV1"]
        ),
        idempotency_key=IDEMPOTENCY_KEY,
    )
    actions.start_ingestion(
        context=context(),
        source_document_id=SOURCE_DOCUMENT_ID,
        source_version_id=SOURCE_VERSION_ID,
        idempotency_key=IDEMPOTENCY_KEY,
    )
    actions.get_ingestion(
        context=context(),
        source_document_id=SOURCE_DOCUMENT_ID,
        source_version_id=SOURCE_VERSION_ID,
        run_id=INGESTION_RUN_ID,
    )

    assert [call.operation for call in service.calls] == [
        "create_admission",
        "review_authorization",
        "create_upload_intent",
        "upload_to_intent",
        "get_admission",
        "cancel_admission",
        "list_operation_authorizations",
        "request_operation_authorization",
        "review_operation_authorization",
        "start_ingestion",
        "get_ingestion",
    ]
    assert all(
        call.tenant_id == ALPHA_TENANT_ID and call.actor_id == ACTOR_ID
        for call in service.calls
        if call.operation != "upload_to_intent"
    )


def test_admin_requires_trusted_tenant_and_bounded_idempotency() -> None:
    examples = load_source_examples()
    service = RecordingSourceAdmissionServiceFake()
    actions = SourceAdmissionAdminActions(service=service)
    request = CreateSourceAdmissionV1.model_validate(examples["CreateSourceAdmissionV1"])

    with pytest.raises(SourceAdmissionContractError) as missing:
        actions.create_admission(
            context=AdminActorContext(actor_id=ACTOR_ID, tenant_id=None),
            request=request,
            idempotency_key=IDEMPOTENCY_KEY,
        )
    with pytest.raises(SourceAdmissionContractError) as invalid:
        actions.create_admission(context=context(), request=request, idempotency_key="short")

    assert missing.value.code == "TENANT_CONTEXT_REQUIRED"
    assert invalid.value.code == "SOURCE_ADMISSION_VALIDATION_FAILED"
    assert service.calls == []


def test_admin_lifecycle_fields_are_read_only_and_has_no_orm_escape_hatch() -> None:
    assert {
        "tenant_id",
        "status",
        "admission_status",
        "content_sha256",
        "derived_local_inspection_result",
        "rejection_code",
        "removal",
        "row_version",
    } <= SOURCE_ADMISSION_READONLY_FIELDS

    tree = ast.parse(
        Path("backend/src/lms/adapters/admin/documents.py").read_text(encoding="utf-8")
    )
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    methods = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert not any(module.endswith(".models") for module in imports)
    assert not any(module.startswith("lms.modules.documents") for module in imports)
    assert {"objects", "save", "delete"}.isdisjoint(attributes)
    assert {"save_model", "delete_model", "save_form"}.isdisjoint(methods)
