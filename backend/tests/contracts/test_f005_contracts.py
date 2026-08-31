from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_f005_openapi_exposes_only_frozen_local_generation_routes_and_schemas() -> None:
    schema = json.loads((REPO_ROOT / "contracts/openapi/openapi.json").read_text(encoding="utf-8"))
    expected = {
        "/api/v1/tenants/{tenant_id}/course-generation-runs": (
            "post",
            "startCourseGeneration",
        ),
        "/api/v1/tenants/{tenant_id}/course-generation-runs/{run_id}": (
            "get",
            "getCourseGeneration",
        ),
        "/api/v1/tenants/{tenant_id}/course-generation-runs/{run_id}/approve-blueprint": (
            "post",
            "approveCourseGenerationBlueprint",
        ),
        "/api/v1/tenants/{tenant_id}/course-generation-runs/{run_id}/reject": (
            "post",
            "rejectCourseGeneration",
        ),
    }
    for path, (method, operation_id) in expected.items():
        assert schema["paths"][path][method]["operationId"] == operation_id
    components = schema["components"]["schemas"]
    assert {
        "StartCourseGenerationV1",
        "ApproveGenerationBlueprintV1",
        "RejectCourseGenerationV1",
        "CourseGenerationRunV1",
        "CourseBlueprintV1",
        "CourseBlueprintItemV1",
        "GeneratedLessonV1",
        "CourseGenerationReviewPackageV1",
    } <= set(components)
    start = components["StartCourseGenerationV1"]
    serialized = json.dumps(start, sort_keys=True)
    assert "provider" not in start["properties"]
    assert "model" not in start["properties"]
    assert "prompt" not in serialized.casefold()
    assert "deterministic-source-course-v1" in json.dumps(
        components["CourseGenerationRunV1"], sort_keys=True
    )


def test_f005_generated_types_are_present_and_marked_generated() -> None:
    generated = (REPO_ROOT / "packages/api-client/src/generated/schema.d.ts").read_text(
        encoding="utf-8"
    )
    assert generated.startswith("// GENERATED from contracts/openapi/openapi.json; DO NOT EDIT.")
    assert 'operations["startCourseGeneration"]' in generated
    assert 'operations["approveCourseGenerationBlueprint"]' in generated
    assert "export type GenerationStatus" in generated
