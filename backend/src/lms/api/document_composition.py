from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from django.conf import settings
from django.db import close_old_connections

from lms.api.schemas.documents import (
    CancelSourceAdmissionV1,
    CreateSourceAdmissionV1,
    RequestedSourceOperation,
    ReviewSourceOperationAuthorizationV1,
    ReviewSourceStoreAuthorizationV1,
    SourceAdmissionContractError,
)
from lms.modules.documents.errors import SourceAdmissionError
from lms.modules.documents.ingestion import DocumentIngestionService
from lms.modules.documents.inspector import LocalPdfInspector
from lms.modules.documents.services import SourceAdmissionService
from lms.modules.documents.storage import LocalQuarantineStorage
from lms.modules.documents.types import (
    CancelAdmissionCommand,
    CreateAdmissionCommand,
    ReviewAuthorizationCommand,
    RightsDeclarationInput,
)


def _translate[Result](call: Callable[[], Result]) -> Result:
    try:
        return call()
    except SourceAdmissionError as error:
        raise SourceAdmissionContractError(
            code=error.code,
            errors=tuple(
                {
                    "location": ("body", *field.path.split(".")),
                    "code": field.code,
                }
                for field in error.field_errors
            ),
        ) from error
    finally:
        close_old_connections()


class DjangoSourceAdmissionService:
    """Compose F-003's local adapters behind the shared application boundary."""

    def __init__(
        self,
        *,
        storage: LocalQuarantineStorage | None = None,
        inspector: LocalPdfInspector | None = None,
    ) -> None:
        quarantine_root = Path(settings.AI_LMS_LOCAL_QUARANTINE_ROOT)
        resolved_storage = storage or LocalQuarantineStorage(quarantine_root)
        self._service = SourceAdmissionService(
            storage=resolved_storage,
            inspector=inspector or LocalPdfInspector(),
        )
        self._ingestion = DocumentIngestionService(storage=resolved_storage)

    def create_admission(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        command: CreateSourceAdmissionV1,
        idempotency_key: str,
    ) -> object:
        rights = command.rights_declaration
        return _translate(
            lambda: self._service.create_admission(
                actor_id=actor_id,
                tenant_id=tenant_id,
                command=CreateAdmissionCommand(
                    display_name=command.display_name,
                    declared_filename=command.declared_filename,
                    rights_declaration=RightsDeclarationInput(
                        basis=rights.basis,
                        attestation_version=rights.attestation_version,
                        attested=rights.attested,
                        rights_holder_name=rights.rights_holder_name,
                        evidence_reference=rights.evidence_reference,
                        valid_until=rights.valid_until,
                    ),
                ),
                idempotency_key=idempotency_key,
            )
        )

    def review_authorization(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        authorization_id: UUID,
        command: ReviewSourceStoreAuthorizationV1,
        idempotency_key: str,
    ) -> object:
        return _translate(
            lambda: self._service.review_authorization(
                actor_id=actor_id,
                tenant_id=tenant_id,
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                authorization_id=authorization_id,
                command=ReviewAuthorizationCommand(
                    decision=command.decision,
                    expected_authorization_row_version=(command.expected_authorization_row_version),
                    decision_code=command.decision_code,
                ),
                idempotency_key=idempotency_key,
            )
        )

    def create_upload_intent(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        idempotency_key: str,
    ) -> object:
        return _translate(
            lambda: self._service.create_upload_intent(
                actor_id=actor_id,
                tenant_id=tenant_id,
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                idempotency_key=idempotency_key,
            )
        )

    def upload_to_intent(
        self,
        *,
        opaque_token: str,
        content_type: str,
        body: bytes,
    ) -> object:
        return _translate(
            lambda: self._service.upload_to_intent(
                opaque_token=opaque_token,
                content_type=content_type,
                body=body,
            )
        )

    def get_admission(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
    ) -> object:
        return _translate(
            lambda: self._service.get_admission(
                actor_id=actor_id,
                tenant_id=tenant_id,
                source_document_id=source_document_id,
                source_version_id=source_version_id,
            )
        )

    def cancel_admission(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        command: CancelSourceAdmissionV1,
        idempotency_key: str,
    ) -> object:
        return _translate(
            lambda: self._service.cancel_admission(
                actor_id=actor_id,
                tenant_id=tenant_id,
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                command=CancelAdmissionCommand(
                    expected_source_version_row_version=(
                        command.expected_source_version_row_version
                    ),
                    reason_code=command.reason_code,
                ),
                idempotency_key=idempotency_key,
            )
        )

    def list_operation_authorizations(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
    ) -> object:
        return _translate(
            lambda: self._service.list_operation_authorizations(
                actor_id=actor_id,
                tenant_id=tenant_id,
                source_document_id=source_document_id,
                source_version_id=source_version_id,
            )
        )

    def request_operation_authorization(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        operation: RequestedSourceOperation,
        idempotency_key: str,
    ) -> object:
        return _translate(
            lambda: self._service.request_operation_authorization(
                actor_id=actor_id,
                tenant_id=tenant_id,
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                operation=operation,
                idempotency_key=idempotency_key,
            )
        )

    def review_operation_authorization(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        operation: RequestedSourceOperation,
        command: ReviewSourceOperationAuthorizationV1,
        idempotency_key: str,
    ) -> object:
        return _translate(
            lambda: self._service.review_operation_authorization(
                actor_id=actor_id,
                tenant_id=tenant_id,
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                operation=operation,
                command=ReviewAuthorizationCommand(
                    decision=command.decision,
                    expected_authorization_row_version=(command.expected_authorization_row_version),
                    decision_code=command.decision_code,
                ),
                idempotency_key=idempotency_key,
            )
        )

    def start_ingestion(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        idempotency_key: str,
    ) -> object:
        return _translate(
            lambda: self._ingestion.start_ingestion(
                actor_id=actor_id,
                tenant_id=tenant_id,
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                idempotency_key=idempotency_key,
            )
        )

    def get_ingestion(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        run_id: UUID,
    ) -> object:
        return _translate(
            lambda: self._ingestion.get_ingestion(
                actor_id=actor_id,
                tenant_id=tenant_id,
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                run_id=run_id,
            )
        )

    def run_ingestion(
        self,
        *,
        tenant_id: UUID,
        run_id: UUID,
        worker_id: str,
    ) -> object:
        return _translate(
            lambda: self._ingestion.run_ingestion(
                tenant_id=tenant_id,
                run_id=run_id,
                worker_id=worker_id,
            )
        )

    def reconcile_pending(self) -> tuple[UUID, ...]:
        return _translate(self._service.reconcile_pending)
