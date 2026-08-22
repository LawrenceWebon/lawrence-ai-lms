from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.tenancy.conftest import tenancy_seed as tenancy_seed


@pytest.fixture
def documents_service(tmp_path: Path) -> Any:
    from lms.modules.documents.inspector import LocalPdfInspector
    from lms.modules.documents.services import SourceAdmissionService
    from lms.modules.documents.storage import LocalQuarantineStorage

    return SourceAdmissionService(
        storage=LocalQuarantineStorage(tmp_path / "quarantine"),
        inspector=LocalPdfInspector(),
    )


@pytest.fixture
def valid_pdf_bytes() -> bytes:
    return Path("backend/tests/documents/fixtures/synthetic-valid-one-page.pdf").read_bytes()
