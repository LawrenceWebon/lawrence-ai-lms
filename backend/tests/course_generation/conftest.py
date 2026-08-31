from __future__ import annotations

from typing import Any

import pytest

from tests.documents.conftest import documents_service as documents_service
from tests.documents.conftest import documents_storage as documents_storage
from tests.documents.conftest import ingestion_service as ingestion_service
from tests.documents.conftest import valid_pdf_bytes as valid_pdf_bytes
from tests.tenancy.conftest import tenancy_seed as tenancy_seed


@pytest.fixture
def generation_service() -> Any:
    from lms.modules.course_generation.services import CourseGenerationService

    return CourseGenerationService()
