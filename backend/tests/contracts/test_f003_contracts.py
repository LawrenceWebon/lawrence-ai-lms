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


def test_f003_fixture_manifest_is_synthetic_and_covers_required_outcomes() -> None:
    manifest = load_json(FIXTURES_PATH)
    fixtures = manifest["fixtures"]
    kinds = {fixture["kind"] for fixture in fixtures}
    outcomes = {fixture["expected_outcome"] for fixture in fixtures}

    assert manifest["classification"] == "synthetic_or_rights_cleared_only"
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
