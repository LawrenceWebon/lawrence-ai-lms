from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.tenancy.conftest import tenancy_seed as tenancy_seed


@pytest.fixture
def documents_storage(tmp_path: Path) -> Any:
    from lms.modules.documents.storage import LocalQuarantineStorage

    return LocalQuarantineStorage(tmp_path / "quarantine")


@pytest.fixture
def documents_service(documents_storage: Any) -> Any:
    from lms.modules.documents.inspector import LocalPdfInspector
    from lms.modules.documents.services import SourceAdmissionService

    return SourceAdmissionService(
        storage=documents_storage,
        inspector=LocalPdfInspector(),
    )


@pytest.fixture
def ingestion_service(documents_storage: Any) -> Any:
    from lms.modules.documents.ingestion import DocumentIngestionService

    return DocumentIngestionService(storage=documents_storage)


@pytest.fixture
def valid_pdf_bytes() -> bytes:
    return Path("backend/tests/documents/fixtures/synthetic-valid-one-page.pdf").read_bytes()
