from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_PATH = REPO_ROOT / "contracts/f003/source-admission.v1.examples.json"

ALPHA_TENANT_ID: Final = UUID("00000000-0000-4000-8000-0000000000a1")
BETA_TENANT_ID: Final = UUID("00000000-0000-4000-8000-0000000000b1")
ACTOR_ID: Final = UUID("00000000-0000-4000-8000-000000000102")
SOURCE_DOCUMENT_ID: Final = UUID("00000000-0000-4000-8000-00000000c301")
SOURCE_VERSION_ID: Final = UUID("00000000-0000-4000-8000-00000000c302")
AUTHORIZATION_ID: Final = UUID("00000000-0000-4000-8000-00000000c304")
INGESTION_RUN_ID: Final = UUID("00000000-0000-4000-8000-00000000c305")
IDEMPOTENCY_KEY: Final = "fixture-source-command-0001"
OPAQUE_TOKEN: Final = "f003localuploadtoken0000000000000001"  # noqa: S105


def load_source_examples() -> dict[str, object]:
    return json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))


@dataclass(frozen=True, slots=True)
class VerifiedActorValue:
    principal_id: UUID


@dataclass(frozen=True, slots=True)
class ServiceCall:
    operation: str
    actor_id: UUID | None = None
    tenant_id: UUID | None = None
    source_document_id: UUID | None = None
    source_version_id: UUID | None = None
    authorization_id: UUID | None = None
    run_id: UUID | None = None
    source_operation: str | None = None
    command: object | None = None
    idempotency_key: str | None = None
    opaque_token: str | None = None
    content_type: str | None = None
    body: bytes | None = None


class RecordingSourceAdmissionServiceFake:
    """Contract-backed fake containing synthetic metadata and no document content."""

    def __init__(self) -> None:
        examples = load_source_examples()
        self.snapshot = examples["SourceAdmissionV1"]
        self.intent = examples["UploadIntentV1"]
        self.operation_authorization = {
            **copy.deepcopy(self.snapshot["store_authorization"]),
            "operation": "extract",
        }
        self.ingestion_run = {
            "id": str(INGESTION_RUN_ID),
            "tenant_id": str(ALPHA_TENANT_ID),
            "source_document_id": str(SOURCE_DOCUMENT_ID),
            "source_version_id": str(SOURCE_VERSION_ID),
            "status": "queued",
            "parser_version": "bounded-local-pypdf-6.16.2-v2",
            "configuration_version": "normalized-source-local-v1",
            "locale": "en",
            "attempt_count": 0,
            "max_attempts": 3,
            "checkpoint": "created",
            "input_manifest_sha256": "sha256:" + "a" * 64,
            "output_manifest_sha256": None,
            "reason_code": None,
            "quality_summary": {},
            "row_version": 1,
            "created_at": "2026-08-31T00:00:00Z",
            "updated_at": "2026-08-31T00:00:00Z",
        }
        self.calls: list[ServiceCall] = []
        self.problem_by_operation: dict[str, Exception] = {}

    def _result(self, operation: str, result: object) -> object:
        problem = self.problem_by_operation.get(operation)
        if problem is not None:
            raise problem
        return copy.deepcopy(result)

    def create_admission(self, **values: object) -> object:
        self.calls.append(ServiceCall(operation="create_admission", **values))
        return self._result("create_admission", self.snapshot)

    def review_authorization(self, **values: object) -> object:
        self.calls.append(ServiceCall(operation="review_authorization", **values))
        return self._result("review_authorization", self.snapshot)

    def create_upload_intent(self, **values: object) -> object:
        self.calls.append(ServiceCall(operation="create_upload_intent", **values))
        return self._result("create_upload_intent", self.intent)

    def upload_to_intent(self, **values: object) -> object:
        self.calls.append(ServiceCall(operation="upload_to_intent", **values))
        return self._result("upload_to_intent", self.snapshot)

    def get_admission(self, **values: object) -> object:
        self.calls.append(ServiceCall(operation="get_admission", **values))
        return self._result("get_admission", self.snapshot)

    def cancel_admission(self, **values: object) -> object:
        self.calls.append(ServiceCall(operation="cancel_admission", **values))
        return self._result("cancel_admission", self.snapshot)

    def list_operation_authorizations(self, **values: object) -> object:
        self.calls.append(ServiceCall(operation="list_operation_authorizations", **values))
        return self._result(
            "list_operation_authorizations",
            [self.operation_authorization],
        )

    def request_operation_authorization(self, **values: object) -> object:
        source_operation = str(values.pop("operation"))
        self.calls.append(
            ServiceCall(
                operation="request_operation_authorization",
                source_operation=source_operation,
                **values,
            )
        )
        return self._result(
            "request_operation_authorization",
            {**self.operation_authorization, "operation": source_operation},
        )

    def review_operation_authorization(self, **values: object) -> object:
        source_operation = str(values.pop("operation"))
        self.calls.append(
            ServiceCall(
                operation="review_operation_authorization",
                source_operation=source_operation,
                **values,
            )
        )
        return self._result(
            "review_operation_authorization",
            {**self.operation_authorization, "operation": source_operation},
        )

    def start_ingestion(self, **values: object) -> object:
        self.calls.append(ServiceCall(operation="start_ingestion", **values))
        return self._result("start_ingestion", self.ingestion_run)

    def get_ingestion(self, **values: object) -> object:
        self.calls.append(ServiceCall(operation="get_ingestion", **values))
        return self._result("get_ingestion", self.ingestion_run)
