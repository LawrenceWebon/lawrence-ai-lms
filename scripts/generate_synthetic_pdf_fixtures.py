from __future__ import annotations

from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_VALID_PDF_PATH = (
    _REPOSITORY_ROOT
    / "backend"
    / "tests"
    / "documents"
    / "fixtures"
    / "synthetic-valid-one-page.pdf"
)


def _pdf_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_valid_pdf() -> bytes:
    text_rows = (
        ("/F1 16 Tf", "Synthetic Course Source", -30),
        ("/F1 13 Tf", "Chapter One: Foundations", -22),
        ("/F1 11 Tf", "Authorized source material explains durable workflows.", -18),
        ("/F1 11 Tf", "Human review protects quality before publication.", -34),
        ("/F1 13 Tf", "Chapter Two: Safe Delivery", -22),
        (
            "/F1 11 Tf",
            "Tenant isolation and immutable provenance protect learners.",
            -18,
        ),
        ("/F1 11 Tf", "Publication is an explicit instructor decision.", 0),
    )
    content_lines = ["BT", "/F1 16 Tf", "72 740 Td"]
    for font, text, downward_offset in text_rows:
        content_lines.extend((font, f"({_pdf_string(text)}) Tj"))
        if downward_offset:
            content_lines.append(f"0 {downward_offset} Td")
    content_lines.append("ET")
    content = ("\n".join(content_lines) + "\n").encode("ascii")

    objects = (
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length "
        + str(len(content)).encode("ascii")
        + b" >>\nstream\n"
        + content
        + b"endstream",
    )

    document = bytearray(b"%PDF-1.7\n% Synthetic deterministic fixture\n")
    offsets = [0]
    for object_number, body in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{object_number} 0 obj\n".encode("ascii"))
        document.extend(body)
        document.extend(b"\nendobj\n")

    xref_offset = len(document)
    document.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    document.extend(b"0000000000 65535 f\n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n\n".encode("ascii"))
    document.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(document)


def main() -> None:
    _VALID_PDF_PATH.write_bytes(_build_valid_pdf())


if __name__ == "__main__":
    main()
