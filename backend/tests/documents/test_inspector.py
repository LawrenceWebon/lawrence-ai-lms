from __future__ import annotations

import zlib
from pathlib import Path

import pytest

from lms.modules.documents import inspector as inspector_module
from lms.modules.documents.inspector import LocalPdfInspector
from lms.modules.documents.policy import ADMISSION_POLICY


def test_local_inspector_derives_admitted_evidence_from_synthetic_pdf(
    valid_pdf_bytes: bytes,
) -> None:
    result = LocalPdfInspector().inspect(valid_pdf_bytes, policy=ADMISSION_POLICY)

    assert result.outcome == "admitted"
    assert result.content_sha256.startswith("sha256:")
    assert result.file_size_bytes == len(valid_pdf_bytes)
    assert result.media_type == "application/pdf"
    assert result.pdf_signature_valid is True
    assert result.parser_accepted is True
    assert result.page_count == 1
    assert result.local_inspection_result == "accepted"
    assert result.rejection_code is None


def test_local_inspector_rejects_signature_encryption_corruption_and_polyglot(
    valid_pdf_bytes: bytes,
) -> None:
    inspector = LocalPdfInspector()

    signature = inspector.inspect(b"not a pdf", policy=ADMISSION_POLICY)
    assert (signature.outcome, signature.rejection_code) == (
        "rejected",
        "PDF_SIGNATURE_MISMATCH",
    )

    encrypted = inspector.inspect(
        valid_pdf_bytes.replace(b"/Catalog", b"/Catalog /Encrypt 9 0 R"),
        policy=ADMISSION_POLICY,
    )
    assert (encrypted.outcome, encrypted.rejection_code) == ("rejected", "PDF_ENCRYPTED")

    corrupt = inspector.inspect(valid_pdf_bytes.removesuffix(b"%%EOF\n"), policy=ADMISSION_POLICY)
    assert (corrupt.outcome, corrupt.rejection_code) == ("rejected", "PDF_CORRUPT")

    polyglot = inspector.inspect(
        valid_pdf_bytes + b"<script>unsafe</script>",
        policy=ADMISSION_POLICY,
    )
    assert (polyglot.outcome, polyglot.rejection_code) == (
        "rejected",
        "PDF_POLYGLOT_REJECTED",
    )


def test_local_inspector_fails_closed_when_capability_is_unavailable(
    valid_pdf_bytes: bytes,
) -> None:
    result = LocalPdfInspector(available=False).inspect(
        valid_pdf_bytes,
        policy=ADMISSION_POLICY,
    )

    assert result.outcome == "retryable_failure"
    assert result.local_inspection_result == "unavailable"
    assert result.rejection_code is None


def test_local_inspector_enforces_byte_and_page_limits(valid_pdf_bytes: bytes) -> None:
    inspector = LocalPdfInspector()

    oversized = inspector.inspect(
        b"%PDF-1.4\n" + b"x" * ADMISSION_POLICY.max_pdf_bytes + b"\n%%EOF\n",
        policy=ADMISSION_POLICY,
    )
    assert oversized.rejection_code == "PDF_SIZE_LIMIT_EXCEEDED"

    pages = b"\n".join(
        [b"%PDF-1.4"]
        + [b"0 0 obj << /Type /Catalog >> endobj"]
        + [
            f"{index} 0 obj << /Type /Page /MediaBox [0 0 10 10] >> endobj".encode()
            for index in range(1, ADMISSION_POLICY.max_page_count + 2)
        ]
        + [b"%%EOF"]
    )
    too_many_pages = inspector.inspect(pages, policy=ADMISSION_POLICY)
    assert too_many_pages.rejection_code == "PDF_PAGE_LIMIT_EXCEEDED"


def test_local_inspector_enforces_per_page_and_total_pixel_limits() -> None:
    inspector = LocalPdfInspector()
    per_page = Path("backend/tests/documents/fixtures/synthetic-pixel-cap.pdf").read_bytes()
    result = inspector.inspect(per_page, policy=ADMISSION_POLICY)
    assert result.rejection_code == "PDF_PIXEL_LIMIT_EXCEEDED"

    pages = b"\n".join(
        [b"%PDF-1.4", b"1 0 obj << /Type /Catalog >> endobj"]
        + [
            f"{index} 0 obj << /Type /Page /MediaBox [0 0 2300 2300] >> endobj".encode()
            for index in range(2, 13)
        ]
        + [b"%%EOF"]
    )
    total = inspector.inspect(pages, policy=ADMISSION_POLICY)
    assert total.max_rendered_pixels_per_page is not None
    assert total.max_rendered_pixels_per_page < ADMISSION_POLICY.max_rendered_pixels_per_page
    assert total.rendered_pixels_total is not None
    assert total.rendered_pixels_total > ADMISSION_POLICY.max_rendered_pixels_total
    assert total.rejection_code == "PDF_PIXEL_LIMIT_EXCEEDED"


def test_local_inspector_bounds_decoded_stream_material() -> None:
    expanded = b"A" * (ADMISSION_POLICY.max_decoded_parser_bytes + 1)
    compressed = zlib.compress(expanded, level=9)
    body = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog >> endobj\n"
        b"2 0 obj << /Type /Page /MediaBox [0 0 10 10] >> endobj\n"
        b"3 0 obj << /Length 100 /Filter /FlateDecode >>\nstream\n"
        + compressed
        + b"\nendstream\nendobj\n%%EOF\n"
    )

    result = LocalPdfInspector().inspect(body, policy=ADMISSION_POLICY)

    assert len(body) < ADMISSION_POLICY.max_pdf_bytes
    assert result.rejection_code == "PDF_DECODED_LIMIT_EXCEEDED"
    assert result.decoded_parser_bytes is not None
    assert result.decoded_parser_bytes > ADMISSION_POLICY.max_decoded_parser_bytes


def test_local_inspector_rejects_unsafe_marker_and_times_out_fail_closed(
    valid_pdf_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unsafe = Path("backend/tests/documents/fixtures/synthetic-unsafe.pdf").read_bytes()
    rejected = LocalPdfInspector().inspect(unsafe, policy=ADMISSION_POLICY)
    assert (rejected.rejection_code, rejected.local_inspection_result) == (
        "PDF_UNSAFE",
        "unsafe",
    )

    wall_times = iter((0.0, ADMISSION_POLICY.validation_wall_seconds + 1.0))
    monkeypatch.setattr(inspector_module.time, "monotonic", lambda: next(wall_times))
    monkeypatch.setattr(inspector_module.time, "process_time", lambda: 0.0)
    timeout = LocalPdfInspector().inspect(valid_pdf_bytes, policy=ADMISSION_POLICY)
    assert timeout.outcome == "retryable_failure"
    assert timeout.local_inspection_result == "unavailable"
    assert timeout.rejection_code is None
