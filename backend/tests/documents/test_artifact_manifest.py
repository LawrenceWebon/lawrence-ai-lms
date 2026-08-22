from __future__ import annotations

import hashlib
import json
from pathlib import Path

from lms.modules.documents.inspector import LocalPdfInspector
from lms.modules.documents.policy import ADMISSION_POLICY

MANIFEST_PATH = Path("backend/tests/documents/fixtures/artifact-manifest.v1.json")


def test_synthetic_artifact_manifest_has_provenance_checksum_and_expected_result() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == "f003-synthetic-artifacts-v1"
    assert manifest["classification"] == "synthetic_only"
    assert len(manifest["artifacts"]) == 7

    inspector = LocalPdfInspector()
    for artifact in manifest["artifacts"]:
        path = Path(artifact["path"])
        body = path.read_bytes()
        assert path.is_relative_to(Path("backend/tests/documents/fixtures"))
        assert artifact["origin"]
        assert artifact["license"] == "CC0-1.0"
        assert artifact["sha256"] == hashlib.sha256(body).hexdigest()
        result = inspector.inspect(body, policy=ADMISSION_POLICY)
        if artifact["expected_rejection_code"] is None:
            assert result.outcome == "admitted"
        else:
            assert result.outcome == "rejected"
            assert result.rejection_code == artifact["expected_rejection_code"]
