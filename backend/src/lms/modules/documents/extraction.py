from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID

EXTRACTION_CONFIGURATION_VERSION = "normalized-source-local-v1"
NORMALIZED_SOURCE_SCHEMA_VERSION = "normalized-source.v1"
_DEFAULT_TIMEOUT_SECONDS = 30
_MAX_PAGE_COUNT = 100
_MAX_EXTRACTED_TEXT_BYTES = 64 * 1024 * 1024
_MAX_PAGE_TEXT_BYTES = 8 * 1024 * 1024

ExtractionOutcome = Literal["extracted", "retryable_failure", "failed"]
ElementKind = Literal["heading", "paragraph"]


@dataclass(frozen=True, slots=True)
class ExtractedPdfPage:
    number: int
    width_points: int | float
    height_points: int | float
    text: str


@dataclass(frozen=True, slots=True)
class PdfExtractionResult:
    outcome: ExtractionOutcome
    pages: tuple[ExtractedPdfPage, ...] = ()
    reason_code: str | None = None


class NormalizationError(Exception):
    def __init__(self, reason_code: str, *, page_numbers: tuple[int, ...] = ()) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.page_numbers = page_numbers


@dataclass(frozen=True, slots=True)
class NormalizedElement:
    id: UUID
    position: int
    kind: ElementKind
    text: str
    text_sha256: str


@dataclass(frozen=True, slots=True)
class NormalizedPage:
    id: UUID
    number: int
    width_points: int | float
    height_points: int | float
    text: str
    text_sha256: str
    ocr_used: bool
    elements: tuple[NormalizedElement, ...]


@dataclass(frozen=True, slots=True)
class NormalizedSection:
    id: UUID
    position: int
    title: str
    start_page: int
    end_page: int
    element_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class NormalizedSource:
    schema_version: str
    source_version_id: UUID
    content_sha256: str
    locale: str
    pages: tuple[NormalizedPage, ...]
    sections: tuple[NormalizedSection, ...]
    projection: dict[str, object]
    canonical_json: str
    markdown: str
    canonical_json_sha256: str
    markdown_sha256: str
    manifest_sha256: str


def _sha256(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _stable_uuid(*parts: object) -> UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, "ai-lms:" + ":".join(str(part) for part in parts))


def _normalized_dimension(value: int | float) -> int | float:
    numeric = float(value)
    if not math.isfinite(numeric) or numeric <= 0:
        raise NormalizationError("DOCUMENT_QUALITY_INSUFFICIENT")
    rounded = round(numeric, 3)
    return int(rounded) if rounded.is_integer() else rounded


def _normalized_text(value: str) -> str:
    canonical_newlines = value.replace("\r\n", "\n").replace("\r", "\n")
    normalized = unicodedata.normalize("NFC", canonical_newlines)
    lines = [line.rstrip() for line in normalized.split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _paragraphs(lines: list[str]) -> tuple[str, ...]:
    paragraphs: list[str] = []
    current: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            current.append(stripped)
        elif current:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return tuple(paragraphs)


class LocalPdfTextExtractor:
    """Extract admitted PDF text in the same bounded child-process envelope."""

    def __init__(self, *, available: bool = True) -> None:
        self._available = available

    def extract(
        self,
        body: bytes,
        *,
        timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS,
    ) -> PdfExtractionResult:
        if not self._available:
            return PdfExtractionResult(
                outcome="retryable_failure",
                reason_code="EXTRACTION_PARSER_FAILED",
            )
        extractor_path = Path(__file__).with_name("pdf_extract.py")
        try:
            completed = subprocess.run(  # noqa: S603
                [sys.executable, "-I", str(extractor_path)],
                check=False,
                input=body,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=timeout_seconds,
                env={},
            )
        except OSError, subprocess.TimeoutExpired:
            return PdfExtractionResult(
                outcome="retryable_failure",
                reason_code="EXTRACTION_PARSER_FAILED",
            )
        if completed.returncode != 0:
            return PdfExtractionResult(
                outcome="retryable_failure",
                reason_code="EXTRACTION_PARSER_FAILED",
            )
        try:
            observation = json.loads(completed.stdout)
        except json.JSONDecodeError, TypeError, UnicodeDecodeError:
            return PdfExtractionResult(
                outcome="retryable_failure",
                reason_code="EXTRACTION_PARSER_FAILED",
            )
        if not isinstance(observation, dict):
            return PdfExtractionResult(
                outcome="retryable_failure",
                reason_code="EXTRACTION_PARSER_FAILED",
            )
        outcome = observation.get("outcome")
        if outcome == "too_large":
            return PdfExtractionResult(
                outcome="failed",
                reason_code="DOCUMENT_QUALITY_INSUFFICIENT",
            )
        if outcome in {"encrypted", "failed"}:
            return PdfExtractionResult(outcome="failed", reason_code="EXTRACTION_PARSER_FAILED")
        if outcome != "extracted":
            return PdfExtractionResult(
                outcome="retryable_failure",
                reason_code="EXTRACTION_PARSER_FAILED",
            )

        raw_pages = observation.get("pages")
        if not isinstance(raw_pages, list) or not 1 <= len(raw_pages) <= _MAX_PAGE_COUNT:
            return PdfExtractionResult(outcome="failed", reason_code="EXTRACTION_PARSER_FAILED")
        pages: list[ExtractedPdfPage] = []
        extracted_bytes = 0
        for expected_number, raw_page in enumerate(raw_pages, start=1):
            if not isinstance(raw_page, dict):
                return PdfExtractionResult(
                    outcome="failed",
                    reason_code="EXTRACTION_PARSER_FAILED",
                )
            number = raw_page.get("number")
            width = raw_page.get("width_points")
            height = raw_page.get("height_points")
            text = raw_page.get("text")
            if (
                number != expected_number
                or isinstance(width, bool)
                or not isinstance(width, (int, float))
                or isinstance(height, bool)
                or not isinstance(height, (int, float))
                or not isinstance(text, str)
                or not math.isfinite(float(width))
                or not math.isfinite(float(height))
                or float(width) <= 0
                or float(height) <= 0
            ):
                return PdfExtractionResult(
                    outcome="failed",
                    reason_code="EXTRACTION_PARSER_FAILED",
                )
            extracted_bytes += len(text.encode("utf-8"))
            if extracted_bytes > _MAX_EXTRACTED_TEXT_BYTES:
                return PdfExtractionResult(
                    outcome="failed",
                    reason_code="DOCUMENT_QUALITY_INSUFFICIENT",
                )
            pages.append(
                ExtractedPdfPage(
                    number=number,
                    width_points=width,
                    height_points=height,
                    text=text,
                )
            )
        return PdfExtractionResult(outcome="extracted", pages=tuple(pages))


def normalize_extracted_pages(
    *,
    tenant_id: UUID,
    source_version_id: UUID,
    content_sha256: str,
    parser_version: str,
    configuration_version: str,
    pages: tuple[ExtractedPdfPage, ...],
) -> NormalizedSource:
    if not 1 <= len(pages) <= _MAX_PAGE_COUNT:
        raise NormalizationError("DOCUMENT_QUALITY_INSUFFICIENT")

    normalized_pages: list[NormalizedPage] = []
    normalized_sections: list[NormalizedSection] = []
    empty_pages: list[int] = []
    for expected_number, extracted_page in enumerate(pages, start=1):
        if extracted_page.number != expected_number:
            raise NormalizationError("DOCUMENT_QUALITY_INSUFFICIENT")
        text = _normalized_text(extracted_page.text)
        if not text:
            empty_pages.append(extracted_page.number)
            continue
        if len(text.encode("utf-8")) > _MAX_PAGE_TEXT_BYTES:
            raise NormalizationError("DOCUMENT_QUALITY_INSUFFICIENT")

        text_sha256 = _sha256(text.encode("utf-8"))
        page_id = _stable_uuid(
            "normalized-page",
            tenant_id,
            source_version_id,
            parser_version,
            configuration_version,
            extracted_page.number,
        )
        lines = text.split("\n")
        first_nonempty = next((line.strip() for line in lines if line.strip()), "")
        heading = first_nonempty if len(first_nonempty) <= 120 else None
        remaining_lines = list(lines)
        if heading is not None:
            first_position = next(
                index for index, line in enumerate(remaining_lines) if line.strip()
            )
            remaining_lines.pop(first_position)

        elements: list[NormalizedElement] = []
        element_values: list[tuple[ElementKind, str]] = []
        if heading is not None:
            element_values.append(("heading", heading))
        element_values.extend(
            ("paragraph", paragraph) for paragraph in _paragraphs(remaining_lines)
        )
        if not element_values:
            raise NormalizationError("DOCUMENT_QUALITY_INSUFFICIENT")
        for position, (kind, element_text) in enumerate(element_values, start=1):
            element_hash = _sha256(element_text.encode("utf-8"))
            element_id = _stable_uuid(
                "normalized-element",
                tenant_id,
                source_version_id,
                parser_version,
                configuration_version,
                extracted_page.number,
                position,
                kind,
                element_hash,
            )
            elements.append(
                NormalizedElement(
                    id=element_id,
                    position=position,
                    kind=kind,
                    text=element_text,
                    text_sha256=element_hash,
                )
            )
        normalized_page = NormalizedPage(
            id=page_id,
            number=extracted_page.number,
            width_points=_normalized_dimension(extracted_page.width_points),
            height_points=_normalized_dimension(extracted_page.height_points),
            text=text,
            text_sha256=text_sha256,
            ocr_used=False,
            elements=tuple(elements),
        )
        normalized_pages.append(normalized_page)

        title = heading or f"Page {extracted_page.number}"
        section_position = len(normalized_sections) + 1
        section_id = _stable_uuid(
            "normalized-section",
            tenant_id,
            source_version_id,
            parser_version,
            configuration_version,
            section_position,
            _sha256(title.encode("utf-8")),
        )
        normalized_sections.append(
            NormalizedSection(
                id=section_id,
                position=section_position,
                title=title,
                start_page=extracted_page.number,
                end_page=extracted_page.number,
                element_ids=tuple(element.id for element in elements),
            )
        )

    if empty_pages:
        raise NormalizationError("OCR_REQUIRED", page_numbers=tuple(empty_pages))

    page_projection: list[dict[str, object]] = []
    for page in normalized_pages:
        page_projection.append(
            {
                "id": str(page.id),
                "number": page.number,
                "width_points": page.width_points,
                "height_points": page.height_points,
                "text_sha256": page.text_sha256,
                "ocr_used": page.ocr_used,
                "elements": [
                    {
                        "id": str(element.id),
                        "position": element.position,
                        "type": element.kind,
                        "text": element.text,
                    }
                    for element in page.elements
                ],
            }
        )
    section_projection = [
        {
            "id": str(section.id),
            "position": section.position,
            "title": section.title,
            "start_page": section.start_page,
            "end_page": section.end_page,
            "element_ids": [str(element_id) for element_id in section.element_ids],
        }
        for section in normalized_sections
    ]
    projection: dict[str, object] = {
        "schema_version": NORMALIZED_SOURCE_SCHEMA_VERSION,
        "source_version_id": str(source_version_id),
        "content_sha256": content_sha256,
        "locale": "en",
        "pages": page_projection,
        "sections": section_projection,
    }
    canonical_json_bytes = _canonical_json(projection)
    markdown_parts: list[str] = ["# Normalized source", ""]
    for section, page in zip(normalized_sections, normalized_pages, strict=True):
        markdown_parts.extend((f"## {section.title}", ""))
        for element in page.elements:
            if element.kind == "heading":
                markdown_parts.extend((f"### {element.text}", ""))
            else:
                markdown_parts.extend((element.text, ""))
    markdown = "\n".join(markdown_parts).rstrip() + "\n"
    canonical_json_sha256 = _sha256(canonical_json_bytes)
    markdown_sha256 = _sha256(markdown.encode("utf-8"))
    manifest_sha256 = _sha256(
        _canonical_json(
            {
                "schema_version": NORMALIZED_SOURCE_SCHEMA_VERSION,
                "tenant_id": str(tenant_id),
                "source_version_id": str(source_version_id),
                "parser_version": parser_version,
                "configuration_version": configuration_version,
                "canonical_json_sha256": canonical_json_sha256,
                "markdown_sha256": markdown_sha256,
                "page_hashes": [page.text_sha256 for page in normalized_pages],
                "section_ids": [str(section.id) for section in normalized_sections],
            }
        )
    )
    return NormalizedSource(
        schema_version=NORMALIZED_SOURCE_SCHEMA_VERSION,
        source_version_id=source_version_id,
        content_sha256=content_sha256,
        locale="en",
        pages=tuple(normalized_pages),
        sections=tuple(normalized_sections),
        projection=projection,
        canonical_json=canonical_json_bytes.decode("utf-8"),
        markdown=markdown,
        canonical_json_sha256=canonical_json_sha256,
        markdown_sha256=markdown_sha256,
        manifest_sha256=manifest_sha256,
    )
