from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest

from lms.api.composition import DjangoTenancyService
from lms.api.document_composition import DjangoSourceAdmissionService
from lms.api.main import create_application
from lms.modules.documents.inspector import LocalPdfInspector
from lms.modules.documents.storage import LocalQuarantineStorage
from lms.modules.identity.entities import IdentityCandidate
from lms.modules.identity.services import IdentityAuthenticationRejectedError
from tests.contract_fakes.f002_course_administration import (
    RecordingCourseAdministrationServiceFake,
)
from tests.documents.conftest import valid_pdf_bytes as valid_pdf_bytes
from tests.tenancy.conftest import tenancy_seed as tenancy_seed

pytestmark = pytest.mark.django_db(transaction=True)


class FixtureIdentityAuthenticator:
    def __init__(self, actors: dict[str, object]) -> None:
        self._actors = actors

    def authenticate(self, *, token: str) -> IdentityCandidate:
        profile = self._actors.get(token)
        if profile is None:
            raise IdentityAuthenticationRejectedError
        return IdentityCandidate(
            principal_id=profile.provider_subject,
            profile_id=profile.id,
            session_id=uuid4(),
            authentication_time=datetime(2026, 8, 22, tzinfo=UTC),
            assurance_level="aal1",
            verified_email=f"{token}@example.invalid",
        )


def headers(token: str, tenant_id: UUID, *, idempotency: str | None = None) -> dict[str, str]:
    result = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
    }
    if idempotency is not None:
        result["Idempotency-Key"] = idempotency
    return result


def send(
    app: object,
    method: str,
    path: str,
    *,
    request_headers: dict[str, str],
    json: object | None = None,
    content: bytes | None = None,
) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(
                method,
                path,
                headers=request_headers,
                json=json,
                content=content,
            )

    return asyncio.run(request())


def create_admission(
    app: object,
    tenant_id: UUID,
    *,
    suffix: str,
) -> dict[str, object]:
    response = send(
        app,
        "POST",
        f"/api/v1/tenants/{tenant_id}/source-documents/admissions",
        request_headers=headers(
            "instructor",
            tenant_id,
            idempotency=f"integration-create-{suffix}-0001",
        ),
        json={
            "display_name": f"Synthetic source {suffix}",
            "declared_filename": f"synthetic-{suffix}.pdf",
            "rights_declaration": {
                "basis": "owned",
                "attestation_version": "f003-source-rights-attestation-v1",
                "attested": True,
            },
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def approve_and_intent(
    app: object,
    tenant_id: UUID,
    snapshot: dict[str, Any],
    *,
    suffix: str,
) -> tuple[dict[str, object], dict[str, object]]:
    document_id = snapshot["source_document"]["id"]
    version_id = snapshot["source_version"]["id"]
    authorization = snapshot["store_authorization"]
    base = f"/api/v1/tenants/{tenant_id}/source-documents/{document_id}/versions/{version_id}"
    approved = send(
        app,
        "POST",
        f"{base}/rights-authorizations/{authorization['id']}/decisions",
        request_headers=headers(
            "admin",
            tenant_id,
            idempotency=f"integration-review-{suffix}-0001",
        ),
        json={
            "decision": "activate",
            "expected_authorization_row_version": authorization["row_version"],
            "decision_code": "RIGHTS_EVIDENCE_ACCEPTED",
        },
    )
    assert approved.status_code == 200, approved.text
    intent = send(
        app,
        "POST",
        f"{base}/upload-intents",
        request_headers=headers(
            "instructor",
            tenant_id,
            idempotency=f"integration-intent-{suffix}-0001",
        ),
    )
    assert intent.status_code == 201, intent.text
    return approved.json(), intent.json()


def test_composed_private_admission_rejection_revocation_and_idor(
    tenancy_seed: dict[str, Any],
    valid_pdf_bytes: bytes,
    tmp_path: Path,
) -> None:
    actors = {
        "instructor": tenancy_seed["profiles"]["instructor"],
        "admin": tenancy_seed["profiles"]["admin"],
        "outsider": tenancy_seed["profiles"]["outsider"],
    }
    document_service = DjangoSourceAdmissionService(
        storage=LocalQuarantineStorage(tmp_path / "quarantine"),
        inspector=LocalPdfInspector(),
    )
    app = create_application(
        identity_authenticator=FixtureIdentityAuthenticator(actors),
        tenancy_service=DjangoTenancyService(),
        course_service=RecordingCourseAdministrationServiceFake(),
        document_service=document_service,
    )
    tenant_id = tenancy_seed["alpha"].id
    beta_id = tenancy_seed["beta"].id

    admitted_request = create_admission(app, tenant_id, suffix="admitted")
    document_id = admitted_request["source_document"]["id"]
    version_id = admitted_request["source_version"]["id"]
    authorization = admitted_request["store_authorization"]
    review_path = (
        f"/api/v1/tenants/{tenant_id}/source-documents/{document_id}/versions/{version_id}"
        f"/rights-authorizations/{authorization['id']}/decisions"
    )
    self_review = send(
        app,
        "POST",
        review_path,
        request_headers=headers(
            "instructor",
            tenant_id,
            idempotency="integration-self-review-0001",
        ),
        json={
            "decision": "activate",
            "expected_authorization_row_version": 1,
            "decision_code": "RIGHTS_EVIDENCE_ACCEPTED",
        },
    )
    assert self_review.status_code == 403
    assert self_review.json()["code"] == "SOURCE_RIGHTS_REVIEWER_SEPARATION_REQUIRED"

    approved, intent = approve_and_intent(
        app,
        tenant_id,
        admitted_request,
        suffix="admitted",
    )
    assert approved["source_version"]["admission_status"] == "upload_pending"
    assert "opaque_token" not in intent
    assert "quarantine" not in str(intent)
    admitted = send(
        app,
        "PUT",
        str(intent["target_url"]),
        request_headers={"Content-Type": "application/pdf"},
        content=valid_pdf_bytes,
    )
    assert admitted.status_code == 202, admitted.text
    assert admitted.json()["source_version"]["admission_status"] == "admitted"

    base = f"/api/v1/tenants/{tenant_id}/source-documents/{document_id}/versions/{version_id}"
    outsider = send(
        app,
        "GET",
        base,
        request_headers=headers("outsider", tenant_id),
    )
    wrong_tenant = send(
        app,
        "GET",
        base.replace(str(tenant_id), str(beta_id), 1),
        request_headers=headers("instructor", beta_id),
    )
    assert outsider.status_code == wrong_tenant.status_code == 404
    assert "Synthetic source admitted" not in outsider.text + wrong_tenant.text

    revoke = send(
        app,
        "POST",
        review_path,
        request_headers=headers(
            "admin",
            tenant_id,
            idempotency="integration-revoke-admitted-0001",
        ),
        json={
            "decision": "revoke",
            "expected_authorization_row_version": 2,
            "decision_code": "RIGHTS_REVOKED",
        },
    )
    assert revoke.status_code == 200, revoke.text
    assert revoke.json()["source_version"]["admission_status"] == "blocked"
    assert revoke.json()["removal"]["status"] == "pending"
    document_service.reconcile_pending()
    reconciled = send(
        app,
        "GET",
        base,
        request_headers=headers("instructor", tenant_id),
    )
    assert reconciled.json()["removal"] == {
        "status": "completed",
        "reason_code": "RIGHTS_REVOKED",
    }

    rejected_request = create_admission(app, tenant_id, suffix="rejected")
    _, rejected_intent = approve_and_intent(
        app,
        tenant_id,
        rejected_request,
        suffix="rejected",
    )
    rejected = send(
        app,
        "PUT",
        str(rejected_intent["target_url"]),
        request_headers={"Content-Type": "application/pdf"},
        content=b"synthetic non-pdf bytes",
    )
    assert rejected.status_code == 202, rejected.text
    assert (
        rejected.json()["source_version"]
        | {
            "admission_status": "rejected",
            "rejection_code": "PDF_SIGNATURE_MISMATCH",
        }
        == rejected.json()["source_version"]
    )
