from __future__ import annotations

from .types import AdmissionPolicy

PERMISSION_SOURCES_READ = "documents.sources.read"
PERMISSION_SOURCES_ADMIT = "documents.sources.admit"
PERMISSION_SOURCES_CANCEL = "documents.sources.cancel"
PERMISSION_SOURCE_RIGHTS_REVIEW = "documents.source_rights.review"
PERMISSION_INGESTION_START = "documents.ingestion.start"
PERMISSION_INGESTION_READ = "documents.ingestion.read"

ADMISSION_POLICY = AdmissionPolicy(
    version="f003-local-v1",
    accepted_media_types=("application/pdf",),
    max_pdf_bytes=6_291_456,
    max_page_count=100,
    max_rendered_pixels_per_page=25_000_000,
    max_rendered_pixels_total=250_000_000,
    max_decoded_parser_bytes=67_108_864,
    validation_cpu_seconds=15,
    validation_wall_seconds=30,
    upload_intent_ttl_seconds=900,
    max_active_upload_intents_per_tenant=2,
    max_upload_intents_per_tenant_24h=10,
    max_upload_attempt_bytes_per_tenant_24h=31_457_280,
    max_quarantine_objects_per_tenant=20,
    max_quarantine_bytes_per_tenant=62_914_560,
)
