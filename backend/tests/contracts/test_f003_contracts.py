from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "contracts/f003/source-admission.v1.schema.json"
EXAMPLES_PATH = REPO_ROOT / "contracts/f003/source-admission.v1.examples.json"
FIXTURES_PATH = REPO_ROOT / "contracts/f003/fixtures/admission-fixtures.v1.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def contract_registry() -> Registry[Any]:
    schema = load_json(SCHEMA_PATH)
    return Registry().with_resources([(schema["$id"], Resource.from_contents(schema))])


def validator_for(dto_name: str) -> Draft202012Validator:
    schema = load_json(SCHEMA_PATH)
    return Draft202012Validator(
        {"$ref": f"{schema['$id']}#/$defs/{dto_name}"},
        registry=contract_registry(),
        format_checker=FormatChecker(),
    )


def walk_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(walk_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(walk_keys(item) for item in value))
    return set()


def test_f003_schema_examples_and_fixture_manifest_are_executable() -> None:
    schema = load_json(SCHEMA_PATH)
    examples = load_json(EXAMPLES_PATH)
    fixtures = load_json(FIXTURES_PATH)

    Draft202012Validator.check_schema(schema)
    for dto_name, example in examples.items():
        validator_for(dto_name).validate(example)
    validator_for("AdmissionFixtureManifestV1").validate(fixtures)


def test_f003_admission_snapshot_has_same_tenant_edges_and_separate_reviewer() -> None:
    snapshot = load_json(EXAMPLES_PATH)["SourceAdmissionV1"]
    tenant_id = snapshot["source_document"]["tenant_id"]
    source_document_id = snapshot["source_document"]["id"]
    source_version_id = snapshot["source_version"]["id"]

    assert snapshot["source_document"]["current_version_id"] == source_version_id
    assert snapshot["source_version"]["tenant_id"] == tenant_id
    assert snapshot["source_version"]["source_document_id"] == source_document_id
    assert snapshot["rights_declaration"]["tenant_id"] == tenant_id
    assert snapshot["rights_declaration"]["source_document_id"] == source_document_id
    assert snapshot["rights_declaration"]["source_version_id"] == source_version_id
    assert snapshot["store_authorization"]["tenant_id"] == tenant_id
    assert snapshot["store_authorization"]["source_document_id"] == source_document_id
    assert snapshot["store_authorization"]["source_version_id"] == source_version_id
    assert (
        snapshot["store_authorization"]["requested_by_actor_id"]
        != snapshot["store_authorization"]["reviewed_by_actor_id"]
    )
    assert snapshot["store_authorization"]["operation"] == "store"


@pytest.mark.parametrize(
    "field",
    [
        "content_sha256",
        "derived_file_size_bytes",
        "derived_media_type",
        "derived_pdf_signature_valid",
        "derived_parser_accepted",
        "derived_page_count",
        "derived_max_rendered_pixels_per_page",
        "derived_rendered_pixels_total",
        "derived_decoded_parser_bytes",
        "derived_local_inspection_result",
    ],
)
def test_f003_admitted_snapshot_requires_byte_derived_evidence(field: str) -> None:
    snapshot = load_json(EXAMPLES_PATH)["SourceAdmissionV1"]
    snapshot["source_version"][field] = None

    with pytest.raises(ValidationError):
        validator_for("SourceAdmissionV1").validate(snapshot)


def test_f003_admitted_snapshot_requires_active_rights_and_no_rejection() -> None:
    snapshot = load_json(EXAMPLES_PATH)["SourceAdmissionV1"]
    snapshot["store_authorization"]["status"] = "revoked"
    with pytest.raises(ValidationError):
        validator_for("SourceAdmissionV1").validate(snapshot)

    snapshot = load_json(EXAMPLES_PATH)["SourceAdmissionV1"]
    snapshot["source_version"]["admission_status"] = "rejected"
    snapshot["source_version"]["rejection_code"] = None
    with pytest.raises(ValidationError):
        validator_for("SourceAdmissionV1").validate(snapshot)


def test_f003_non_rejected_snapshot_cannot_carry_terminal_rejection() -> None:
    snapshot = load_json(EXAMPLES_PATH)["SourceAdmissionV1"]
    snapshot["source_version"]["admission_status"] = "quarantined"
    snapshot["source_version"]["rejection_code"] = "PDF_UNSAFE"

    with pytest.raises(ValidationError):
        validator_for("SourceAdmissionV1").validate(snapshot)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("derived_file_size_bytes", 6_291_457),
        ("derived_pdf_signature_valid", False),
        ("derived_parser_accepted", False),
        ("derived_page_count", 101),
        ("derived_max_rendered_pixels_per_page", 25_000_001),
        ("derived_rendered_pixels_total", 250_000_001),
        ("derived_decoded_parser_bytes", 67_108_865),
        ("derived_local_inspection_result", "unsafe"),
        ("validation_attempt_count", 0),
    ],
)
def test_f003_admitted_snapshot_rejects_failed_or_over_limit_evidence(
    field: str, value: object
) -> None:
    snapshot = load_json(EXAMPLES_PATH)["SourceAdmissionV1"]
    snapshot["source_version"][field] = value

    with pytest.raises(ValidationError):
        validator_for("SourceAdmissionV1").validate(snapshot)

    snapshot = load_json(EXAMPLES_PATH)["SourceAdmissionV1"]
    snapshot["source_version"]["rejection_code"] = "PDF_UNSAFE"
    with pytest.raises(ValidationError):
        validator_for("SourceAdmissionV1").validate(snapshot)


@pytest.mark.parametrize(
    "field",
    [
        "content_sha256",
        "file_size_bytes",
        "media_type",
        "pdf_signature_valid",
        "parser_accepted",
        "page_count",
        "max_rendered_pixels_per_page",
        "rendered_pixels_total",
        "decoded_parser_bytes",
        "local_inspection_result",
    ],
)
def test_f003_admitted_validation_requires_bounded_observation(field: str) -> None:
    result = load_json(EXAMPLES_PATH)["AdmissionValidationResultV1"]
    result[field] = None

    with pytest.raises(ValidationError):
        validator_for("AdmissionValidationResultV1").validate(result)


def test_f003_validation_outcome_and_rejection_reason_are_consistent() -> None:
    admitted = load_json(EXAMPLES_PATH)["AdmissionValidationResultV1"]
    admitted["rejection_code"] = "PDF_UNSAFE"
    with pytest.raises(ValidationError):
        validator_for("AdmissionValidationResultV1").validate(admitted)

    rejected = load_json(EXAMPLES_PATH)["AdmissionValidationResultV1"]
    rejected["outcome"] = "rejected"
    rejected["rejection_code"] = None
    with pytest.raises(ValidationError):
        validator_for("AdmissionValidationResultV1").validate(rejected)

    retryable = load_json(EXAMPLES_PATH)["AdmissionValidationResultV1"]
    retryable.update(
        {
            "outcome": "retryable_failure",
            "content_sha256": None,
            "file_size_bytes": None,
            "media_type": None,
            "pdf_signature_valid": None,
            "parser_accepted": None,
            "page_count": None,
            "max_rendered_pixels_per_page": None,
            "rendered_pixels_total": None,
            "decoded_parser_bytes": None,
            "local_inspection_result": "unavailable",
            "rejection_code": None,
        }
    )
    validator_for("AdmissionValidationResultV1").validate(retryable)

    retryable["rejection_code"] = "INSPECTOR_UNAVAILABLE"
    with pytest.raises(ValidationError):
        validator_for("AdmissionValidationResultV1").validate(retryable)


@pytest.mark.parametrize(
    ("rejection_code", "evidence"),
    [
        ("PDF_SIGNATURE_MISMATCH", {"pdf_signature_valid": False}),
        ("PDF_MEDIA_TYPE_INVALID", {"media_type": "text/plain"}),
        ("PDF_ENCRYPTED", {"parser_accepted": False}),
        ("PDF_CORRUPT", {"parser_accepted": False}),
        ("PDF_POLYGLOT_REJECTED", {"parser_accepted": False}),
        ("PDF_SIZE_LIMIT_EXCEEDED", {"file_size_bytes": 6_291_457}),
        ("PDF_PAGE_LIMIT_EXCEEDED", {"page_count": 101}),
        (
            "PDF_PIXEL_LIMIT_EXCEEDED",
            {"max_rendered_pixels_per_page": 25_000_001},
        ),
        ("PDF_DECODED_LIMIT_EXCEEDED", {"decoded_parser_bytes": 67_108_865}),
        ("PDF_UNSAFE", {"local_inspection_result": "unsafe"}),
        (
            "OBJECT_MISSING",
            {
                "content_sha256": None,
                "file_size_bytes": None,
                "media_type": None,
                "pdf_signature_valid": None,
                "parser_accepted": None,
                "page_count": None,
                "max_rendered_pixels_per_page": None,
                "rendered_pixels_total": None,
                "decoded_parser_bytes": None,
                "local_inspection_result": None,
            },
        ),
        ("OBJECT_CHECKSUM_MISMATCH", {}),
    ],
)
def test_f003_rejected_validation_binds_frozen_reason_to_evidence(
    rejection_code: str, evidence: dict[str, object]
) -> None:
    result = load_json(EXAMPLES_PATH)["AdmissionValidationResultV1"]
    result.update({"outcome": "rejected", "rejection_code": rejection_code})
    result.update(evidence)

    validator_for("AdmissionValidationResultV1").validate(result)


def test_f003_rejected_validation_rejects_contradictory_or_unfrozen_reason() -> None:
    validator = validator_for("AdmissionValidationResultV1")

    result = load_json(EXAMPLES_PATH)["AdmissionValidationResultV1"]
    result.update({"outcome": "rejected", "rejection_code": "PDF_CORRUPT"})
    with pytest.raises(ValidationError):
        validator.validate(result)

    result["rejection_code"] = "UNFROZEN_REASON"
    with pytest.raises(ValidationError):
        validator.validate(result)

    result.update(
        {
            "rejection_code": "PDF_CORRUPT",
            "parser_accepted": False,
            "local_inspection_result": "unavailable",
        }
    )
    with pytest.raises(ValidationError):
        validator.validate(result)


def test_f003_retryable_validation_requires_unavailable_nonterminal_result() -> None:
    validator = validator_for("AdmissionValidationResultV1")
    result = load_json(EXAMPLES_PATH)["AdmissionValidationResultV1"]
    result.update({"outcome": "retryable_failure", "rejection_code": None})

    with pytest.raises(ValidationError):
        validator.validate(result)

    result["local_inspection_result"] = "unsafe"
    with pytest.raises(ValidationError):
        validator.validate(result)

    result["local_inspection_result"] = "unavailable"
    validator.validate(result)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("file_size_bytes", 6_291_457),
        ("pdf_signature_valid", False),
        ("parser_accepted", False),
        ("page_count", 101),
        ("max_rendered_pixels_per_page", 25_000_001),
        ("rendered_pixels_total", 250_000_001),
        ("decoded_parser_bytes", 67_108_865),
        ("local_inspection_result", "unsafe"),
    ],
)
def test_f003_admitted_validation_rejects_failed_or_over_limit_evidence(
    field: str, value: object
) -> None:
    result = load_json(EXAMPLES_PATH)["AdmissionValidationResultV1"]
    result[field] = value

    with pytest.raises(ValidationError):
        validator_for("AdmissionValidationResultV1").validate(result)


def test_f003_local_policy_has_the_owner_approved_q_p03_values() -> None:
    policy = load_json(EXAMPLES_PATH)["AdmissionPolicyV1"]

    assert policy == {
        "version": "f003-local-v1",
        "accepted_media_types": ["application/pdf"],
        "max_pdf_bytes": 6_291_456,
        "max_page_count": 100,
        "max_rendered_pixels_per_page": 25_000_000,
        "max_rendered_pixels_total": 250_000_000,
        "max_decoded_parser_bytes": 67_108_864,
        "validation_cpu_seconds": 15,
        "validation_wall_seconds": 30,
        "upload_intent_ttl_seconds": 900,
        "max_active_upload_intents_per_tenant": 2,
        "max_upload_intents_per_tenant_24h": 10,
        "max_upload_attempt_bytes_per_tenant_24h": 31_457_280,
        "max_quarantine_objects_per_tenant": 20,
        "max_quarantine_bytes_per_tenant": 62_914_560,
    }


def test_f003_contract_rejects_unknown_or_unsafe_transport_fields() -> None:
    examples = load_json(EXAMPLES_PATH)

    create_command = copy.deepcopy(examples["CreateSourceAdmissionV1"])
    create_command["tenant_id"] = "00000000-0000-4000-8000-0000000000a1"
    with pytest.raises(ValidationError):
        validator_for("CreateSourceAdmissionV1").validate(create_command)

    validation_job = copy.deepcopy(examples["AdmissionValidationJobV1"])
    validation_job["storage_key"] = "private/path/that-must-not-cross-the-port"
    with pytest.raises(ValidationError):
        validator_for("AdmissionValidationJobV1").validate(validation_job)

    event = copy.deepcopy(examples["SourceAdmissionEventV1"])
    event["payload"]["source_text"] = "untrusted source body"
    with pytest.raises(ValidationError):
        validator_for("SourceAdmissionEventV1").validate(event)


def test_f003_rights_evidence_and_decision_discriminators_are_strict() -> None:
    examples = load_json(EXAMPLES_PATH)

    create_command = copy.deepcopy(examples["CreateSourceAdmissionV1"])
    create_command["rights_declaration"]["basis"] = "licensed"
    with pytest.raises(ValidationError):
        validator_for("CreateSourceAdmissionV1").validate(create_command)

    review_command = copy.deepcopy(examples["ReviewSourceStoreAuthorizationV1"])
    review_command["decision"] = "deny"
    with pytest.raises(ValidationError):
        validator_for("ReviewSourceStoreAuthorizationV1").validate(review_command)


def test_f003_jobs_and_events_do_not_carry_source_content_or_storage_secrets() -> None:
    examples = load_json(EXAMPLES_PATH)
    protected_keys = {
        "source_bytes",
        "source_text",
        "storage_key",
        "target_url",
        "upload_token",
        "rights_holder_name",
        "evidence_reference",
    }

    assert protected_keys.isdisjoint(walk_keys(examples["AdmissionValidationJobV1"]))
    assert protected_keys.isdisjoint(walk_keys(examples["SourceRemovalJobV1"]))
    assert protected_keys.isdisjoint(walk_keys(examples["SourceAdmissionEventV1"]))


def test_f003_event_uses_repository_envelope_and_binds_type_to_payload() -> None:
    event = load_json(EXAMPLES_PATH)["SourceAdmissionEventV1"]
    validator = validator_for("SourceAdmissionEventV1")
    required_envelope = {
        "producer",
        "aggregate_type",
        "aggregate_id",
        "aggregate_version",
        "recorded_at",
        "causation_id",
        "privacy_class",
    }

    assert required_envelope.issubset(event)
    assert event["producer"] == "documents"
    assert event["aggregate_type"] == "source_version"
    assert event["aggregate_id"] == event["source_version_id"]
    validator.validate(event)

    for field in required_envelope:
        missing = copy.deepcopy(event)
        del missing[field]
        with pytest.raises(ValidationError):
            validator.validate(missing)

    mismatched = copy.deepcopy(event)
    mismatched["event_type"] = "source.rights.declared.v1"
    with pytest.raises(ValidationError):
        validator.validate(mismatched)


@pytest.mark.parametrize(
    ("event_type", "admission_status", "content_sha256", "reason_code"),
    [
        ("source.rights.declared.v1", "rights_pending", None, None),
        ("source.store_authorization.activated.v1", "upload_pending", None, None),
        ("source.version.quarantined.v1", "quarantined", None, None),
        ("source.admission.validation_requested.v1", "quarantined", None, None),
        (
            "source.version.admitted.v1",
            "admitted",
            "sha256:577a863e821823c16490e2acbc6c30b086a45c90d6efefea815b8bc4bd99fb1d",
            None,
        ),
        ("source.version.rejected.v1", "rejected", None, "PDF_CORRUPT"),
        ("source.version.cancelled.v1", "cancelled", None, "USER_CANCELLED"),
        ("source.rights.revoked.v1", "blocked", None, "RIGHTS_REVOKED"),
        ("source.removal.completed.v1", "blocked", None, "RIGHTS_REVOKED"),
    ],
)
def test_f003_all_event_facts_have_discriminated_payloads(
    event_type: str,
    admission_status: str,
    content_sha256: str | None,
    reason_code: str | None,
) -> None:
    event = load_json(EXAMPLES_PATH)["SourceAdmissionEventV1"]
    event["event_type"] = event_type
    event["payload"] = {
        "admission_status": admission_status,
        "content_sha256": content_sha256,
        "reason_code": reason_code,
    }

    validator_for("SourceAdmissionEventV1").validate(event)


@pytest.mark.parametrize(
    ("event_type", "admission_status", "reason_code"),
    [
        ("source.version.rejected.v1", "rejected", "USER_CANCELLED"),
        ("source.version.cancelled.v1", "cancelled", "PDF_CORRUPT"),
        ("source.removal.completed.v1", "blocked", "UNFROZEN_REASON"),
    ],
)
def test_f003_event_reason_family_must_match_event_type(
    event_type: str, admission_status: str, reason_code: str
) -> None:
    event = load_json(EXAMPLES_PATH)["SourceAdmissionEventV1"]
    event["event_type"] = event_type
    event["payload"] = {
        "admission_status": admission_status,
        "content_sha256": None,
        "reason_code": reason_code,
    }

    with pytest.raises(ValidationError):
        validator_for("SourceAdmissionEventV1").validate(event)


def test_f003_fixture_manifest_is_synthetic_and_covers_required_outcomes() -> None:
    manifest = load_json(FIXTURES_PATH)
    fixtures = manifest["fixtures"]
    kinds = {fixture["kind"] for fixture in fixtures}
    outcomes = {fixture["expected_outcome"] for fixture in fixtures}

    assert manifest["classification"] == "synthetic_or_rights_cleared_only"
    assert manifest["artifact_scope"] == "scenario_metadata_only"
    assert manifest["artifact_provenance_status"] == "required_from_implementation_issue_43"
    assert {
        "valid_pdf",
        "signature_mismatch",
        "encrypted_pdf",
        "corrupt_pdf",
        "page_limit",
        "pixel_limit",
        "size_limit",
        "validation_unavailable",
        "object_missing",
        "checksum_mismatch",
    }.issubset(kinds)
    assert outcomes == {"admitted", "rejected", "retryable_failure"}
