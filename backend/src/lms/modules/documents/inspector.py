from __future__ import annotations

import hashlib
import math
import re
import time
import zlib
from typing import TypedDict

from .types import AdmissionPolicy, AdmissionValidationResult

INSPECTOR_VERSION = "bounded-local-pdf-inspector-v1"
_PAGE_PATTERN = re.compile(rb"/Type\s*/Page(?!s)\b")
_MEDIA_BOX_PATTERN = re.compile(
    rb"/MediaBox\s*\[\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+"
    rb"(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\]"
)
_UNSAFE_MARKERS = (b"/JavaScript", b"/JS ", b"/Launch", b"/EmbeddedFile")
_STREAM_PATTERN = re.compile(
    rb"(?P<dictionary><<.*?>>)\s*stream\r?\n(?P<body>.*?)\r?\nendstream",
    re.DOTALL,
)


class _CommonPdfObservation(TypedDict):
    body: bytes
    media_type: str
    signature: bool


class LocalPdfInspector:
    """Bounded, network-free structural inspection for local synthetic fixtures.

    This intentionally does not claim production malware detection or full PDF parsing.
    Any unknown structural observation fails closed.
    """

    def __init__(self, *, available: bool = True) -> None:
        self._available = available

    @staticmethod
    def _result(
        *,
        outcome: str,
        body: bytes | None,
        rejection_code: str | None = None,
        media_type: str | None = None,
        signature: bool | None = None,
        parser_accepted: bool | None = None,
        page_count: int | None = None,
        per_page_pixels: int | None = None,
        total_pixels: int | None = None,
        decoded_bytes: int | None = None,
        inspection: str | None = None,
    ) -> AdmissionValidationResult:
        return AdmissionValidationResult(
            outcome=outcome,  # type: ignore[arg-type]
            inspector_version=INSPECTOR_VERSION,
            content_sha256=(None if body is None else f"sha256:{hashlib.sha256(body).hexdigest()}"),
            file_size_bytes=None if body is None else len(body),
            media_type=media_type,
            pdf_signature_valid=signature,
            parser_accepted=parser_accepted,
            page_count=page_count,
            max_rendered_pixels_per_page=per_page_pixels,
            rendered_pixels_total=total_pixels,
            decoded_parser_bytes=decoded_bytes,
            local_inspection_result=inspection,  # type: ignore[arg-type]
            rejection_code=rejection_code,
        )

    def inspect(self, body: bytes, *, policy: AdmissionPolicy) -> AdmissionValidationResult:
        started_wall = time.monotonic()
        started_cpu = time.process_time()
        if not self._available:
            return self._result(
                outcome="retryable_failure",
                body=None,
                inspection="unavailable",
            )
        if len(body) > policy.max_pdf_bytes:
            return self._result(
                outcome="rejected",
                body=body,
                rejection_code="PDF_SIZE_LIMIT_EXCEEDED",
            )
        if not body.startswith(b"%PDF-"):
            return self._result(
                outcome="rejected",
                body=body,
                rejection_code="PDF_SIGNATURE_MISMATCH",
                media_type="application/octet-stream",
                signature=False,
            )

        common: _CommonPdfObservation = {
            "body": body,
            "media_type": "application/pdf",
            "signature": True,
        }
        eof = body.rfind(b"%%EOF")
        if eof < 0:
            return self._result(
                outcome="rejected",
                rejection_code="PDF_CORRUPT",
                parser_accepted=False,
                **common,
            )
        if body[eof + len(b"%%EOF") :].strip():
            return self._result(
                outcome="rejected",
                rejection_code="PDF_POLYGLOT_REJECTED",
                parser_accepted=False,
                **common,
            )
        if b"/Encrypt" in body:
            return self._result(
                outcome="rejected",
                rejection_code="PDF_ENCRYPTED",
                parser_accepted=False,
                **common,
            )

        page_count = len(_PAGE_PATTERN.findall(body))
        if page_count < 1 or b"/Catalog" not in body:
            return self._result(
                outcome="rejected",
                rejection_code="PDF_CORRUPT",
                parser_accepted=False,
                page_count=page_count,
                **common,
            )
        if page_count > policy.max_page_count:
            return self._result(
                outcome="rejected",
                rejection_code="PDF_PAGE_LIMIT_EXCEEDED",
                parser_accepted=True,
                page_count=page_count,
                **common,
            )

        media_boxes = _MEDIA_BOX_PATTERN.findall(body)
        if not media_boxes:
            return self._result(
                outcome="rejected",
                rejection_code="PDF_CORRUPT",
                parser_accepted=False,
                page_count=page_count,
                **common,
            )
        pixels: list[int] = []
        for left, bottom, right, top in media_boxes:
            width_points = abs(float(right) - float(left))
            height_points = abs(float(top) - float(bottom))
            if width_points <= 0 or height_points <= 0:
                return self._result(
                    outcome="rejected",
                    rejection_code="PDF_CORRUPT",
                    parser_accepted=False,
                    page_count=page_count,
                    **common,
                )
            width_pixels = math.ceil(width_points * 150 / 72)
            height_pixels = math.ceil(height_points * 150 / 72)
            pixels.append(width_pixels * height_pixels)
        if len(pixels) < page_count:
            pixels.extend([pixels[-1]] * (page_count - len(pixels)))
        max_pixels = max(pixels)
        total_pixels = sum(pixels[:page_count])
        if (
            max_pixels > policy.max_rendered_pixels_per_page
            or total_pixels > policy.max_rendered_pixels_total
        ):
            return self._result(
                outcome="rejected",
                rejection_code="PDF_PIXEL_LIMIT_EXCEEDED",
                parser_accepted=True,
                page_count=page_count,
                per_page_pixels=max_pixels,
                total_pixels=total_pixels,
                **common,
            )

        decoded_bytes = len(body)
        for stream in _STREAM_PATTERN.finditer(body):
            dictionary = stream.group("dictionary")
            stream_body = stream.group("body")
            if b"/Filter" in dictionary and b"/FlateDecode" not in dictionary:
                return self._result(
                    outcome="rejected",
                    rejection_code="PDF_UNSAFE",
                    parser_accepted=False,
                    page_count=page_count,
                    per_page_pixels=max_pixels,
                    total_pixels=total_pixels,
                    decoded_bytes=decoded_bytes,
                    inspection="unsafe",
                    **common,
                )
            if b"/FlateDecode" not in dictionary:
                decoded_bytes += len(stream_body)
                continue
            remaining = policy.max_decoded_parser_bytes - decoded_bytes
            if remaining < 0:
                break
            try:
                decompressor = zlib.decompressobj()
                decoded = decompressor.decompress(stream_body, remaining + 1)
                decoded_bytes += len(decoded)
                if decoded_bytes <= policy.max_decoded_parser_bytes:
                    decoded_bytes += len(
                        decompressor.flush(policy.max_decoded_parser_bytes - decoded_bytes + 1)
                    )
            except zlib.error:
                return self._result(
                    outcome="rejected",
                    rejection_code="PDF_CORRUPT",
                    parser_accepted=False,
                    page_count=page_count,
                    per_page_pixels=max_pixels,
                    total_pixels=total_pixels,
                    decoded_bytes=decoded_bytes,
                    **common,
                )
            if not decompressor.eof:
                if decoded_bytes > policy.max_decoded_parser_bytes:
                    break
                return self._result(
                    outcome="rejected",
                    rejection_code="PDF_CORRUPT",
                    parser_accepted=False,
                    page_count=page_count,
                    per_page_pixels=max_pixels,
                    total_pixels=total_pixels,
                    decoded_bytes=decoded_bytes,
                    **common,
                )
        if decoded_bytes > policy.max_decoded_parser_bytes:
            return self._result(
                outcome="rejected",
                rejection_code="PDF_DECODED_LIMIT_EXCEEDED",
                parser_accepted=True,
                page_count=page_count,
                per_page_pixels=max_pixels,
                total_pixels=total_pixels,
                decoded_bytes=decoded_bytes,
                **common,
            )
        if any(marker in body for marker in _UNSAFE_MARKERS):
            return self._result(
                outcome="rejected",
                rejection_code="PDF_UNSAFE",
                parser_accepted=True,
                page_count=page_count,
                per_page_pixels=max_pixels,
                total_pixels=total_pixels,
                decoded_bytes=decoded_bytes,
                inspection="unsafe",
                **common,
            )
        if (
            time.monotonic() - started_wall > policy.validation_wall_seconds
            or time.process_time() - started_cpu > policy.validation_cpu_seconds
        ):
            return self._result(
                outcome="retryable_failure",
                parser_accepted=True,
                page_count=page_count,
                per_page_pixels=max_pixels,
                total_pixels=total_pixels,
                decoded_bytes=decoded_bytes,
                inspection="unavailable",
                **common,
            )
        return self._result(
            outcome="admitted",
            parser_accepted=True,
            page_count=page_count,
            per_page_pixels=max_pixels,
            total_pixels=total_pixels,
            decoded_bytes=decoded_bytes,
            inspection="accepted",
            **common,
        )
