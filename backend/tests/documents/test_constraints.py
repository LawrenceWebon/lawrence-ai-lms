from __future__ import annotations

from typing import Any

import pytest
from django.db import DatabaseError, IntegrityError, transaction

from lms.modules.documents.models import (
    SourceDocument,
    SourceRightsDeclaration,
    SourceUseAuthorization,
    SourceVersion,
)
from lms.modules.documents.types import CreateAdmissionCommand, RightsDeclarationInput


def command() -> CreateAdmissionCommand:
    return CreateAdmissionCommand(
        display_name="Synthetic constraint source",
        declared_filename="synthetic-constraint.pdf",
        rights_declaration=RightsDeclarationInput(
            basis="owned",
            attestation_version="f003-source-rights-attestation-v1",
            attested=True,
        ),
    )


@pytest.mark.django_db
def test_composite_foreign_keys_reject_cross_tenant_source_edges(
    tenancy_seed: dict[str, Any], documents_service: Any
) -> None:
    created = documents_service.create_admission(
        actor_id=tenancy_seed["profiles"]["instructor"].provider_subject,
        tenant_id=tenancy_seed["alpha"].id,
        command=command(),
        idempotency_key="constraint-source-create-0001",
    )
    alpha_document = SourceDocument.objects.get(id=created.source_document.id)

    with pytest.raises(IntegrityError), transaction.atomic():
        SourceVersion.objects.create(
            tenant=tenancy_seed["beta"],
            source_document=alpha_document,
            version_number=2,
            declared_filename="cross-tenant.pdf",
        )


@pytest.mark.django_db
def test_database_rejects_same_actor_review_and_invalid_admitted_evidence(
    tenancy_seed: dict[str, Any], documents_service: Any
) -> None:
    created = documents_service.create_admission(
        actor_id=tenancy_seed["profiles"]["instructor"].provider_subject,
        tenant_id=tenancy_seed["alpha"].id,
        command=command(),
        idempotency_key="constraint-source-create-0002",
    )
    authorization = SourceUseAuthorization.objects.get(id=created.store_authorization.id)
    authorization.status = "active"
    authorization.reviewed_by_actor_id = authorization.requested_by_actor_id
    authorization.decision_code = "RIGHTS_EVIDENCE_ACCEPTED"
    authorization.valid_from = authorization.created_at
    with pytest.raises(IntegrityError), transaction.atomic():
        authorization.save()

    version = SourceVersion.objects.get(id=created.source_version.id)
    version.admission_status = "admitted"
    with pytest.raises(IntegrityError), transaction.atomic():
        version.save()


@pytest.mark.django_db
def test_rights_declaration_and_terminal_source_state_are_immutable(
    tenancy_seed: dict[str, Any], documents_service: Any
) -> None:
    created = documents_service.create_admission(
        actor_id=tenancy_seed["profiles"]["instructor"].provider_subject,
        tenant_id=tenancy_seed["alpha"].id,
        command=command(),
        idempotency_key="constraint-source-create-0003",
    )
    declaration = SourceRightsDeclaration.objects.get(id=created.rights_declaration.id)
    declaration.evidence_reference = "changed-after-attestation"
    with pytest.raises(DatabaseError), transaction.atomic():
        declaration.save()

    version = SourceVersion.objects.get(id=created.source_version.id)
    version.admission_status = "cancelled"
    version.row_version += 1
    version.save()
    version.admission_status = "upload_pending"
    version.row_version += 1
    with pytest.raises(DatabaseError), transaction.atomic():
        version.save()
