from __future__ import annotations

import uuid

from django.db import migrations

DOCUMENT_PERMISSIONS = {
    "documents.sources.read": "Read tenant source-admission status",
    "documents.sources.admit": "Declare and upload private PDF sources",
    "documents.sources.cancel": "Cancel tenant source admissions",
    "documents.source_rights.review": "Review operation-scoped source rights",
}
ROLE_PERMISSION_CODES = {
    "tenant_admin": tuple(sorted(DOCUMENT_PERMISSIONS)),
    "instructor": (
        "documents.sources.admit",
        "documents.sources.cancel",
        "documents.sources.read",
    ),
    "reviewer": (),
    "learner": (),
}


def seed_document_permissions(apps, schema_editor):
    del schema_editor
    Permission = apps.get_model("tenancy", "Permission")
    Role = apps.get_model("tenancy", "Role")
    RolePermission = apps.get_model("tenancy", "RolePermission")
    permissions = {}
    for code, description in DOCUMENT_PERMISSIONS.items():
        permission, _ = Permission.objects.get_or_create(
            id=uuid.uuid5(uuid.NAMESPACE_URL, f"ai-lms:permission:{code}"),
            defaults={"code": code, "description": description},
        )
        permissions[code] = permission
    for role in Role.objects.filter(code__in=ROLE_PERMISSION_CODES):
        for code in ROLE_PERMISSION_CODES[role.code]:
            RolePermission.objects.get_or_create(
                tenant_id=role.tenant_id,
                role_id=role.id,
                permission_id=permissions[code].id,
            )


def unseed_document_permissions(apps, schema_editor):
    del schema_editor
    Permission = apps.get_model("tenancy", "Permission")
    RolePermission = apps.get_model("tenancy", "RolePermission")
    permission_ids = list(
        Permission.objects.filter(code__in=DOCUMENT_PERMISSIONS).values_list("id", flat=True)
    )
    RolePermission.objects.filter(permission_id__in=permission_ids).delete()
    Permission.objects.filter(id__in=permission_ids).delete()


FORWARD_SQL = r"""
DO $roles$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lms_worker_runtime') THEN
        CREATE ROLE lms_worker_runtime
            LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
    END IF;
END
$roles$;

GRANT USAGE ON SCHEMA app, audit, integration TO lms_worker_runtime;

ALTER TABLE app.source_documents OWNER TO lms_object_owner;
ALTER TABLE app.source_document_versions OWNER TO lms_object_owner;
ALTER TABLE app.source_rights_declarations OWNER TO lms_object_owner;
ALTER TABLE app.source_use_authorizations OWNER TO lms_object_owner;
ALTER TABLE app.source_upload_intents OWNER TO lms_object_owner;
ALTER TABLE app.source_storage_objects OWNER TO lms_object_owner;
ALTER TABLE integration.document_jobs OWNER TO lms_object_owner;
ALTER TABLE integration.document_job_attempts OWNER TO lms_object_owner;

REVOKE ALL ON app.source_documents, app.source_document_versions,
    app.source_rights_declarations, app.source_use_authorizations,
    app.source_upload_intents, app.source_storage_objects,
    integration.document_jobs, integration.document_job_attempts FROM PUBLIC;

ALTER TABLE app.source_document_versions
    ADD CONSTRAINT fk_source_versions_same_tenant_document
    FOREIGN KEY (tenant_id, source_document_id)
    REFERENCES app.source_documents (tenant_id, id) ON DELETE RESTRICT;
ALTER TABLE app.source_documents
    ADD CONSTRAINT fk_source_documents_current_version
    FOREIGN KEY (tenant_id, current_version_id)
    REFERENCES app.source_document_versions (tenant_id, id) ON DELETE RESTRICT;
ALTER TABLE app.source_rights_declarations
    ADD CONSTRAINT fk_source_rights_same_tenant_document
    FOREIGN KEY (tenant_id, source_document_id)
    REFERENCES app.source_documents (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_source_rights_same_tenant_version
    FOREIGN KEY (tenant_id, source_version_id)
    REFERENCES app.source_document_versions (tenant_id, id) ON DELETE RESTRICT;
ALTER TABLE app.source_use_authorizations
    ADD CONSTRAINT fk_source_auth_same_tenant_document
    FOREIGN KEY (tenant_id, source_document_id)
    REFERENCES app.source_documents (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_source_auth_same_tenant_version
    FOREIGN KEY (tenant_id, source_version_id)
    REFERENCES app.source_document_versions (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_source_auth_same_tenant_declaration
    FOREIGN KEY (tenant_id, rights_declaration_id)
    REFERENCES app.source_rights_declarations (tenant_id, id) ON DELETE RESTRICT;
ALTER TABLE app.source_upload_intents
    ADD CONSTRAINT fk_source_intents_same_tenant_document
    FOREIGN KEY (tenant_id, source_document_id)
    REFERENCES app.source_documents (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_source_intents_same_tenant_version
    FOREIGN KEY (tenant_id, source_version_id)
    REFERENCES app.source_document_versions (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_source_intents_same_tenant_authorization
    FOREIGN KEY (tenant_id, authorization_id)
    REFERENCES app.source_use_authorizations (tenant_id, id) ON DELETE RESTRICT;
ALTER TABLE app.source_storage_objects
    ADD CONSTRAINT fk_source_objects_same_tenant_document
    FOREIGN KEY (tenant_id, source_document_id)
    REFERENCES app.source_documents (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_source_objects_same_tenant_version
    FOREIGN KEY (tenant_id, source_version_id)
    REFERENCES app.source_document_versions (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_source_objects_same_tenant_intent
    FOREIGN KEY (tenant_id, upload_intent_id)
    REFERENCES app.source_upload_intents (tenant_id, id) ON DELETE RESTRICT;
ALTER TABLE integration.document_jobs
    ADD CONSTRAINT fk_document_jobs_same_tenant_document
    FOREIGN KEY (tenant_id, source_document_id)
    REFERENCES app.source_documents (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_document_jobs_same_tenant_version
    FOREIGN KEY (tenant_id, source_version_id)
    REFERENCES app.source_document_versions (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_document_jobs_same_tenant_object
    FOREIGN KEY (tenant_id, storage_object_id)
    REFERENCES app.source_storage_objects (tenant_id, id) ON DELETE RESTRICT;
ALTER TABLE integration.document_job_attempts
    ADD CONSTRAINT fk_document_attempts_same_tenant_job
    FOREIGN KEY (tenant_id, job_id)
    REFERENCES integration.document_jobs (tenant_id, id) ON DELETE RESTRICT;

ALTER TABLE app.source_document_versions
    ADD CONSTRAINT ck_source_versions_rejection_shape CHECK (
        (admission_status = 'rejected' AND rejection_code IS NOT NULL)
        OR (admission_status <> 'rejected' AND rejection_code IS NULL)
    ),
    ADD CONSTRAINT ck_source_versions_admitted_evidence CHECK (
        admission_status <> 'admitted' OR (
            content_sha256 IS NOT NULL
            AND derived_file_size_bytes BETWEEN 1 AND 6291456
            AND derived_media_type = 'application/pdf'
            AND derived_pdf_signature_valid IS TRUE
            AND derived_parser_accepted IS TRUE
            AND derived_page_count BETWEEN 1 AND 100
            AND derived_max_rendered_pixels_per_page BETWEEN 1 AND 25000000
            AND derived_rendered_pixels_total BETWEEN 1 AND 250000000
            AND derived_decoded_parser_bytes BETWEEN 0 AND 67108864
            AND derived_local_inspection_result = 'accepted'
            AND validation_attempt_count >= 1
        )
    ),
    ADD CONSTRAINT ck_source_versions_removal_shape CHECK (
        (removal_status = 'not_required' AND removal_reason_code IS NULL)
        OR (
            removal_status IN ('pending', 'completed', 'failed')
            AND removal_reason_code IN (
                'USER_CANCELLED', 'RIGHTS_REVOKED', 'RIGHTS_EXPIRED', 'RIGHTS_DISPUTED'
            )
        )
    );
ALTER TABLE app.source_use_authorizations
    ADD CONSTRAINT ck_source_auth_reviewer_separation CHECK (
        reviewed_by_actor_id IS NULL OR reviewed_by_actor_id <> requested_by_actor_id
    ),
    ADD CONSTRAINT ck_source_auth_decision_shape CHECK (
        (status = 'requested' AND reviewed_by_actor_id IS NULL AND decision_code IS NULL)
        OR (status = 'active' AND decision_code = 'RIGHTS_EVIDENCE_ACCEPTED'
            AND reviewed_by_actor_id IS NOT NULL AND valid_from IS NOT NULL)
        OR (status = 'denied' AND decision_code = 'RIGHTS_EVIDENCE_INSUFFICIENT'
            AND reviewed_by_actor_id IS NOT NULL)
        OR (status = 'revoked' AND decision_code = 'RIGHTS_REVOKED'
            AND reviewed_by_actor_id IS NOT NULL)
        OR (status = 'expired' AND decision_code = 'RIGHTS_EXPIRED')
        OR (status = 'disputed' AND decision_code = 'RIGHTS_DISPUTED')
    );
ALTER TABLE app.source_upload_intents
    ADD CONSTRAINT ck_source_intents_observation_shape CHECK (
        (status = 'consumed' AND observed_content_sha256 IS NOT NULL
            AND observed_byte_count IS NOT NULL)
        OR (status <> 'consumed' AND observed_content_sha256 IS NULL
            AND observed_byte_count IS NULL)
    ),
    ADD CONSTRAINT ck_source_intents_checksum CHECK (
        observed_content_sha256 IS NULL
        OR observed_content_sha256 ~ '^sha256:[0-9a-f]{64}$'
    ),
    ADD CONSTRAINT ck_source_intents_upload_claim CHECK (
        (upload_claim_digest IS NULL AND upload_claim_expires_at IS NULL)
        OR (status = 'active' AND upload_claim_digest ~ '^[0-9a-f]{64}$'
            AND upload_claim_expires_at IS NOT NULL)
    );
ALTER TABLE app.source_storage_objects
    ADD CONSTRAINT ck_source_objects_positive_bytes CHECK (byte_count >= 1),
    ADD CONSTRAINT ck_source_objects_pdf_media CHECK (media_type = 'application/pdf'),
    ADD CONSTRAINT ck_source_objects_removal_time CHECK (
        (status = 'deleted' AND removed_at IS NOT NULL)
        OR (status <> 'deleted' AND removed_at IS NULL)
    );
ALTER TABLE integration.document_jobs
    ADD CONSTRAINT ck_document_jobs_output_hash CHECK (
        output_manifest_sha256 IS NULL
        OR output_manifest_sha256 ~ '^sha256:[0-9a-f]{64}$'
    ),
    ADD CONSTRAINT ck_document_jobs_lease_shape CHECK (
        (status = 'claimed' AND lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL)
        OR (status <> 'claimed' AND lease_owner IS NULL AND lease_expires_at IS NULL)
    ),
    ADD CONSTRAINT ck_document_jobs_attempt_bounds CHECK (
        attempt_count <= max_attempts AND max_attempts BETWEEN 1 AND 10
    );
ALTER TABLE integration.document_job_attempts
    ADD CONSTRAINT ck_document_attempts_observation_object CHECK (
        jsonb_typeof(observation) = 'object'
    ),
    ADD CONSTRAINT ck_document_attempts_input_hash CHECK (
        input_manifest_sha256 ~ '^sha256:[0-9a-f]{64}$'
    ),
    ADD CONSTRAINT ck_document_attempts_output_hash CHECK (
        output_manifest_sha256 IS NULL
        OR output_manifest_sha256 ~ '^sha256:[0-9a-f]{64}$'
    );

CREATE OR REPLACE FUNCTION app.current_upload_token_digest()
RETURNS text
LANGUAGE sql
STABLE
SET search_path = pg_catalog
AS $$
    SELECT NULLIF(current_setting('app.current_upload_token_digest', true), '')
$$;
CREATE OR REPLACE FUNCTION app.current_job_id()
RETURNS uuid
LANGUAGE sql
STABLE
SET search_path = pg_catalog
AS $$
    SELECT NULLIF(current_setting('app.current_job_id', true), '')::uuid
$$;
CREATE OR REPLACE FUNCTION app.current_job_stage()
RETURNS text
LANGUAGE sql
STABLE
SET search_path = pg_catalog
AS $$
    SELECT NULLIF(current_setting('app.current_job_stage', true), '')
$$;
CREATE OR REPLACE FUNCTION app.has_upload_intent_scope(
    target_tenant_id uuid,
    target_source_version_id uuid
)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, app
SET row_security = off
AS $$
    SELECT app.current_upload_token_digest() IS NOT NULL
       AND EXISTS (
            SELECT 1
              FROM app.source_upload_intents intent
             WHERE intent.tenant_id = target_tenant_id
               AND intent.source_version_id = target_source_version_id
               AND intent.token_digest = app.current_upload_token_digest()
               AND intent.status IN ('active', 'consumed')
       )
$$;
CREATE OR REPLACE FUNCTION app.has_service_job_scope(
    target_tenant_id uuid,
    target_source_version_id uuid,
    required_stage text
)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, integration
SET row_security = off
AS $$
    SELECT app.current_job_id() IS NOT NULL
       AND app.current_job_stage() = required_stage
       AND EXISTS (
            SELECT 1
              FROM integration.document_jobs job
             WHERE job.id = app.current_job_id()
               AND job.tenant_id = target_tenant_id
               AND job.source_version_id = target_source_version_id
               AND job.stage = required_stage
       )
$$;

REVOKE ALL ON FUNCTION app.current_upload_token_digest() FROM PUBLIC;
REVOKE ALL ON FUNCTION app.current_job_id() FROM PUBLIC;
REVOKE ALL ON FUNCTION app.current_job_stage() FROM PUBLIC;
REVOKE ALL ON FUNCTION app.has_upload_intent_scope(uuid, uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION app.has_service_job_scope(uuid, uuid, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app.current_upload_token_digest() TO lms_api_runtime;
GRANT EXECUTE ON FUNCTION app.current_job_id() TO lms_api_runtime, lms_worker_runtime;
GRANT EXECUTE ON FUNCTION app.current_job_stage() TO lms_api_runtime, lms_worker_runtime;
GRANT EXECUTE ON FUNCTION app.has_upload_intent_scope(uuid, uuid) TO lms_api_runtime;
GRANT EXECUTE ON FUNCTION app.has_service_job_scope(uuid, uuid, text)
    TO lms_api_runtime, lms_worker_runtime;

CREATE OR REPLACE FUNCTION app.reject_source_rights_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    RAISE EXCEPTION 'source-rights declarations are immutable' USING ERRCODE = '55000';
END
$$;
REVOKE ALL ON FUNCTION app.reject_source_rights_mutation() FROM PUBLIC;

CREATE OR REPLACE FUNCTION app.enforce_source_document_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'source documents are retained for the approved local evidence boundary'
            USING ERRCODE = '55000';
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id
       OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
       OR NEW.display_name IS DISTINCT FROM OLD.display_name
       OR NEW.owner_actor_id IS DISTINCT FROM OLD.owner_actor_id
       OR NEW.created_at IS DISTINCT FROM OLD.created_at
       OR (
            OLD.current_version_id IS NOT NULL
            AND NEW.current_version_id IS DISTINCT FROM OLD.current_version_id
       ) THEN
        RAISE EXCEPTION 'source-document identity is immutable' USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION app.enforce_source_document_mutation() FROM PUBLIC;

CREATE OR REPLACE FUNCTION app.enforce_source_authorization_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'source authorizations are retained' USING ERRCODE = '55000';
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id
       OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
       OR NEW.source_document_id IS DISTINCT FROM OLD.source_document_id
       OR NEW.source_version_id IS DISTINCT FROM OLD.source_version_id
       OR NEW.rights_declaration_id IS DISTINCT FROM OLD.rights_declaration_id
       OR NEW.operation IS DISTINCT FROM OLD.operation
       OR NEW.requested_by_actor_id IS DISTINCT FROM OLD.requested_by_actor_id
       OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'source-authorization identity is immutable' USING ERRCODE = '55000';
    END IF;
    IF OLD.status = 'requested' AND NEW.status NOT IN ('requested', 'active', 'denied') THEN
        RAISE EXCEPTION 'invalid source-authorization transition' USING ERRCODE = '23514';
    ELSIF OLD.status = 'active'
       AND NEW.status NOT IN ('active', 'revoked', 'expired', 'disputed') THEN
        RAISE EXCEPTION 'invalid source-authorization transition' USING ERRCODE = '23514';
    ELSIF OLD.status IN ('denied', 'revoked', 'expired', 'disputed')
       AND NEW.status <> OLD.status THEN
        RAISE EXCEPTION 'terminal source authorization is immutable' USING ERRCODE = '23514';
    END IF;
    IF NEW.status IS DISTINCT FROM OLD.status AND NEW.row_version <> OLD.row_version + 1 THEN
        RAISE EXCEPTION 'source-authorization transition requires the next row version'
            USING ERRCODE = '23514';
    END IF;
    IF OLD.status <> 'requested' AND NEW.status = OLD.status AND (
        NEW.reviewed_by_actor_id IS DISTINCT FROM OLD.reviewed_by_actor_id
        OR NEW.decision_code IS DISTINCT FROM OLD.decision_code
        OR NEW.valid_from IS DISTINCT FROM OLD.valid_from
        OR NEW.valid_until IS DISTINCT FROM OLD.valid_until
    ) THEN
        RAISE EXCEPTION 'source-authorization decision evidence is immutable'
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION app.enforce_source_authorization_mutation() FROM PUBLIC;

CREATE OR REPLACE FUNCTION app.enforce_source_intent_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'source upload intents are retained' USING ERRCODE = '55000';
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id
       OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
       OR NEW.source_document_id IS DISTINCT FROM OLD.source_document_id
       OR NEW.source_version_id IS DISTINCT FROM OLD.source_version_id
       OR NEW.authorization_id IS DISTINCT FROM OLD.authorization_id
       OR NEW.token_digest IS DISTINCT FROM OLD.token_digest
       OR NEW.purpose IS DISTINCT FROM OLD.purpose
       OR NEW.expires_at IS DISTINCT FROM OLD.expires_at
       OR NEW.max_bytes IS DISTINCT FROM OLD.max_bytes
       OR NEW.accepted_media_type IS DISTINCT FROM OLD.accepted_media_type
       OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'source upload-intent scope is immutable' USING ERRCODE = '55000';
    END IF;
    IF OLD.status = 'active'
       AND NEW.status NOT IN ('active', 'consumed', 'expired', 'cancelled') THEN
        RAISE EXCEPTION 'invalid source upload-intent transition' USING ERRCODE = '23514';
    ELSIF OLD.status <> 'active' AND NEW.status <> OLD.status THEN
        RAISE EXCEPTION 'terminal source upload intent is immutable' USING ERRCODE = '23514';
    END IF;
    IF NEW.status IS DISTINCT FROM OLD.status AND NEW.row_version <> OLD.row_version + 1 THEN
        RAISE EXCEPTION 'source upload-intent transition requires the next row version'
            USING ERRCODE = '23514';
    END IF;
    IF OLD.status <> 'active' AND (
        NEW.observed_content_sha256 IS DISTINCT FROM OLD.observed_content_sha256
        OR NEW.observed_byte_count IS DISTINCT FROM OLD.observed_byte_count
        OR NEW.upload_claim_digest IS DISTINCT FROM OLD.upload_claim_digest
        OR NEW.upload_claim_expires_at IS DISTINCT FROM OLD.upload_claim_expires_at
    ) THEN
        RAISE EXCEPTION 'terminal source upload-intent evidence is immutable'
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION app.enforce_source_intent_mutation() FROM PUBLIC;

CREATE OR REPLACE FUNCTION app.enforce_source_version_mutation()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, app
SET row_security = off
AS $$
DECLARE
    runtime_role text := current_setting('role', true);
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'source versions are retained for the approved local evidence boundary'
            USING ERRCODE = '55000';
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id
       OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
       OR NEW.source_document_id IS DISTINCT FROM OLD.source_document_id
       OR NEW.version_number IS DISTINCT FROM OLD.version_number
       OR NEW.declared_filename IS DISTINCT FROM OLD.declared_filename THEN
        RAISE EXCEPTION 'source-version identity and declared evidence are immutable'
            USING ERRCODE = '55000';
    END IF;
    IF OLD.admission_status = 'rights_pending'
       AND NEW.admission_status NOT IN ('rights_pending', 'upload_pending', 'rejected', 'cancelled') THEN
        RAISE EXCEPTION 'invalid source admission transition' USING ERRCODE = '23514';
    ELSIF OLD.admission_status = 'upload_pending'
       AND NEW.admission_status NOT IN (
           'upload_pending', 'quarantined', 'rejected', 'cancelled', 'blocked'
       ) THEN
        RAISE EXCEPTION 'invalid source admission transition' USING ERRCODE = '23514';
    ELSIF OLD.admission_status = 'quarantined'
       AND NEW.admission_status NOT IN (
           'quarantined', 'validating', 'rejected', 'cancelled', 'blocked'
       ) THEN
        RAISE EXCEPTION 'invalid source admission transition' USING ERRCODE = '23514';
    ELSIF OLD.admission_status = 'validating'
       AND NEW.admission_status NOT IN (
           'validating', 'admitted', 'rejected', 'quarantined', 'cancelled', 'blocked'
       ) THEN
        RAISE EXCEPTION 'invalid source admission transition' USING ERRCODE = '23514';
    ELSIF OLD.admission_status = 'admitted'
       AND NEW.admission_status NOT IN ('admitted', 'blocked') THEN
        RAISE EXCEPTION 'admitted source versions can only be blocked' USING ERRCODE = '23514';
    ELSIF OLD.admission_status IN ('rejected', 'cancelled', 'blocked')
       AND NEW.admission_status <> OLD.admission_status THEN
        RAISE EXCEPTION 'terminal source admission state is immutable' USING ERRCODE = '23514';
    END IF;
    IF runtime_role = 'lms_api_runtime' AND (
        NEW.content_sha256 IS DISTINCT FROM OLD.content_sha256
        OR NEW.derived_file_size_bytes IS DISTINCT FROM OLD.derived_file_size_bytes
        OR NEW.derived_media_type IS DISTINCT FROM OLD.derived_media_type
        OR NEW.derived_pdf_signature_valid IS DISTINCT FROM OLD.derived_pdf_signature_valid
        OR NEW.derived_parser_accepted IS DISTINCT FROM OLD.derived_parser_accepted
        OR NEW.derived_page_count IS DISTINCT FROM OLD.derived_page_count
        OR NEW.derived_max_rendered_pixels_per_page IS DISTINCT FROM
            OLD.derived_max_rendered_pixels_per_page
        OR NEW.derived_rendered_pixels_total IS DISTINCT FROM OLD.derived_rendered_pixels_total
        OR NEW.derived_decoded_parser_bytes IS DISTINCT FROM OLD.derived_decoded_parser_bytes
        OR NEW.derived_local_inspection_result IS DISTINCT FROM
            OLD.derived_local_inspection_result
        OR NEW.validation_attempt_count IS DISTINCT FROM OLD.validation_attempt_count
    ) AND NOT app.has_upload_intent_scope(OLD.tenant_id, OLD.id)
      AND NOT app.has_service_job_scope(
          OLD.tenant_id, OLD.id, app.current_job_stage()
      ) THEN
        RAISE EXCEPTION 'trusted admission observation scope is required'
            USING ERRCODE = '42501';
    END IF;
    RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION app.enforce_source_version_mutation() FROM PUBLIC;

CREATE OR REPLACE FUNCTION app.enforce_source_object_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'source object inventory is reconciled, not deleted'
            USING ERRCODE = '55000';
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id
       OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
       OR NEW.source_document_id IS DISTINCT FROM OLD.source_document_id
       OR NEW.source_version_id IS DISTINCT FROM OLD.source_version_id
       OR NEW.upload_intent_id IS DISTINCT FROM OLD.upload_intent_id
       OR NEW.private_locator IS DISTINCT FROM OLD.private_locator
       OR NEW.content_sha256 IS DISTINCT FROM OLD.content_sha256
       OR NEW.byte_count IS DISTINCT FROM OLD.byte_count
       OR NEW.media_type IS DISTINCT FROM OLD.media_type
       OR NEW.observed_at IS DISTINCT FROM OLD.observed_at THEN
        RAISE EXCEPTION 'source object observation is immutable' USING ERRCODE = '55000';
    END IF;
    IF OLD.status = 'present' AND NEW.status NOT IN ('present', 'missing', 'deleted') THEN
        RAISE EXCEPTION 'invalid source-object transition' USING ERRCODE = '23514';
    ELSIF OLD.status IN ('missing', 'deleted') AND NEW.status <> OLD.status THEN
        RAISE EXCEPTION 'terminal source-object inventory is immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION app.enforce_source_object_mutation() FROM PUBLIC;

CREATE OR REPLACE FUNCTION integration.enforce_document_job_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'document jobs are retained' USING ERRCODE = '55000';
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id
       OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
       OR NEW.source_document_id IS DISTINCT FROM OLD.source_document_id
       OR NEW.source_version_id IS DISTINCT FROM OLD.source_version_id
       OR NEW.storage_object_id IS DISTINCT FROM OLD.storage_object_id
       OR NEW.stage IS DISTINCT FROM OLD.stage
       OR NEW.max_attempts IS DISTINCT FROM OLD.max_attempts
       OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key
       OR NEW.correlation_id IS DISTINCT FROM OLD.correlation_id
       OR NEW.input_manifest_sha256 IS DISTINCT FROM OLD.input_manifest_sha256
       OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'document-job scope is immutable' USING ERRCODE = '55000';
    END IF;
    IF OLD.status = 'pending' AND NEW.status NOT IN ('pending', 'claimed', 'cancelled') THEN
        RAISE EXCEPTION 'invalid document-job transition' USING ERRCODE = '23514';
    ELSIF OLD.status = 'claimed'
       AND NEW.status NOT IN ('claimed', 'completed', 'retryable', 'failed', 'cancelled') THEN
        RAISE EXCEPTION 'invalid document-job transition' USING ERRCODE = '23514';
    ELSIF OLD.status = 'retryable' AND NEW.status NOT IN ('retryable', 'claimed', 'cancelled') THEN
        RAISE EXCEPTION 'invalid document-job transition' USING ERRCODE = '23514';
    ELSIF OLD.status IN ('completed', 'failed', 'cancelled') AND NEW.status <> OLD.status THEN
        RAISE EXCEPTION 'terminal document job is immutable' USING ERRCODE = '23514';
    END IF;
    IF NEW.status IS DISTINCT FROM OLD.status AND NEW.row_version <> OLD.row_version + 1 THEN
        RAISE EXCEPTION 'document-job transition requires the next row version'
            USING ERRCODE = '23514';
    END IF;
    IF NEW.attempt_count < OLD.attempt_count OR NEW.attempt_count > OLD.attempt_count + 1 THEN
        RAISE EXCEPTION 'document-job attempts advance one at a time' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION integration.enforce_document_job_mutation() FROM PUBLIC;

CREATE OR REPLACE FUNCTION integration.enforce_document_attempt_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    IF TG_OP = 'DELETE' OR OLD.outcome <> 'running' THEN
        RAISE EXCEPTION 'completed document-job attempts are immutable'
            USING ERRCODE = '55000';
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id
       OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
       OR NEW.job_id IS DISTINCT FROM OLD.job_id
       OR NEW.attempt_number IS DISTINCT FROM OLD.attempt_number
       OR NEW.input_manifest_sha256 IS DISTINCT FROM OLD.input_manifest_sha256
       OR NEW.started_at IS DISTINCT FROM OLD.started_at THEN
        RAISE EXCEPTION 'document-job attempt identity is immutable'
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION integration.enforce_document_attempt_mutation() FROM PUBLIC;

CREATE TRIGGER source_rights_immutable
BEFORE UPDATE OR DELETE ON app.source_rights_declarations
FOR EACH ROW EXECUTE FUNCTION app.reject_source_rights_mutation();
CREATE TRIGGER source_documents_immutable_identity
BEFORE UPDATE OR DELETE ON app.source_documents
FOR EACH ROW EXECUTE FUNCTION app.enforce_source_document_mutation();
CREATE TRIGGER source_versions_lifecycle
BEFORE UPDATE OR DELETE ON app.source_document_versions
FOR EACH ROW EXECUTE FUNCTION app.enforce_source_version_mutation();
CREATE TRIGGER source_objects_immutable_observation
BEFORE UPDATE OR DELETE ON app.source_storage_objects
FOR EACH ROW EXECUTE FUNCTION app.enforce_source_object_mutation();
CREATE TRIGGER source_authorizations_lifecycle
BEFORE UPDATE OR DELETE ON app.source_use_authorizations
FOR EACH ROW EXECUTE FUNCTION app.enforce_source_authorization_mutation();
CREATE TRIGGER source_upload_intents_lifecycle
BEFORE UPDATE OR DELETE ON app.source_upload_intents
FOR EACH ROW EXECUTE FUNCTION app.enforce_source_intent_mutation();
CREATE TRIGGER document_jobs_lifecycle
BEFORE UPDATE OR DELETE ON integration.document_jobs
FOR EACH ROW EXECUTE FUNCTION integration.enforce_document_job_mutation();
CREATE TRIGGER document_attempts_immutable
BEFORE UPDATE OR DELETE ON integration.document_job_attempts
FOR EACH ROW EXECUTE FUNCTION integration.enforce_document_attempt_mutation();

ALTER TABLE app.source_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.source_documents FORCE ROW LEVEL SECURITY;
CREATE POLICY source_documents_select ON app.source_documents FOR SELECT TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'documents.sources.read')
        OR app.has_permission(tenant_id, 'documents.source_rights.review')
        OR app.has_upload_intent_scope(tenant_id, current_version_id)
        OR app.has_service_job_scope(tenant_id, current_version_id, app.current_job_stage())
    );
CREATE POLICY source_documents_insert ON app.source_documents FOR INSERT TO lms_api_runtime
    WITH CHECK (app.has_permission(tenant_id, 'documents.sources.admit'));
CREATE POLICY source_documents_update ON app.source_documents FOR UPDATE TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'documents.sources.admit'))
    WITH CHECK (app.has_permission(tenant_id, 'documents.sources.admit'));
CREATE POLICY source_documents_worker_select ON app.source_documents
    FOR SELECT TO lms_worker_runtime
    USING (app.has_service_job_scope(tenant_id, current_version_id, app.current_job_stage()));

ALTER TABLE app.source_document_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.source_document_versions FORCE ROW LEVEL SECURITY;
CREATE POLICY source_versions_select ON app.source_document_versions FOR SELECT TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'documents.sources.read')
        OR app.has_permission(tenant_id, 'documents.source_rights.review')
        OR app.has_upload_intent_scope(tenant_id, id)
        OR app.has_service_job_scope(tenant_id, id, app.current_job_stage())
    );
CREATE POLICY source_versions_insert ON app.source_document_versions FOR INSERT TO lms_api_runtime
    WITH CHECK (app.has_permission(tenant_id, 'documents.sources.admit'));
CREATE POLICY source_versions_update ON app.source_document_versions FOR UPDATE TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'documents.sources.admit')
        OR app.has_permission(tenant_id, 'documents.sources.cancel')
        OR app.has_permission(tenant_id, 'documents.source_rights.review')
        OR app.has_upload_intent_scope(tenant_id, id)
        OR app.has_service_job_scope(tenant_id, id, app.current_job_stage())
    )
    WITH CHECK (
        app.has_permission(tenant_id, 'documents.sources.admit')
        OR app.has_permission(tenant_id, 'documents.sources.cancel')
        OR app.has_permission(tenant_id, 'documents.source_rights.review')
        OR app.has_upload_intent_scope(tenant_id, id)
        OR app.has_service_job_scope(tenant_id, id, app.current_job_stage())
    );
CREATE POLICY source_versions_worker ON app.source_document_versions
    FOR SELECT TO lms_worker_runtime
    USING (app.has_service_job_scope(tenant_id, id, app.current_job_stage()));
CREATE POLICY source_versions_worker_update ON app.source_document_versions
    FOR UPDATE TO lms_worker_runtime
    USING (app.has_service_job_scope(tenant_id, id, app.current_job_stage()))
    WITH CHECK (app.has_service_job_scope(tenant_id, id, app.current_job_stage()));

ALTER TABLE app.source_rights_declarations ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.source_rights_declarations FORCE ROW LEVEL SECURITY;
CREATE POLICY source_rights_select ON app.source_rights_declarations FOR SELECT TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'documents.sources.read')
        OR app.has_permission(tenant_id, 'documents.source_rights.review')
        OR app.has_upload_intent_scope(tenant_id, source_version_id)
        OR app.has_service_job_scope(tenant_id, source_version_id, app.current_job_stage())
    );
CREATE POLICY source_rights_insert ON app.source_rights_declarations FOR INSERT TO lms_api_runtime
    WITH CHECK (app.has_permission(tenant_id, 'documents.sources.admit'));
CREATE POLICY source_rights_worker_select ON app.source_rights_declarations
    FOR SELECT TO lms_worker_runtime
    USING (app.has_service_job_scope(tenant_id, source_version_id, app.current_job_stage()));

ALTER TABLE app.source_use_authorizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.source_use_authorizations FORCE ROW LEVEL SECURITY;
CREATE POLICY source_auth_select ON app.source_use_authorizations FOR SELECT TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'documents.sources.read')
        OR app.has_permission(tenant_id, 'documents.source_rights.review')
        OR app.has_upload_intent_scope(tenant_id, source_version_id)
        OR app.has_service_job_scope(tenant_id, source_version_id, app.current_job_stage())
    );
CREATE POLICY source_auth_insert ON app.source_use_authorizations FOR INSERT TO lms_api_runtime
    WITH CHECK (app.has_permission(tenant_id, 'documents.sources.admit'));
CREATE POLICY source_auth_update ON app.source_use_authorizations FOR UPDATE TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'documents.source_rights.review'))
    WITH CHECK (app.has_permission(tenant_id, 'documents.source_rights.review'));
CREATE POLICY source_auth_worker_select ON app.source_use_authorizations
    FOR SELECT TO lms_worker_runtime
    USING (app.has_service_job_scope(tenant_id, source_version_id, app.current_job_stage()));

ALTER TABLE app.source_upload_intents ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.source_upload_intents FORCE ROW LEVEL SECURITY;
CREATE POLICY source_intents_select ON app.source_upload_intents FOR SELECT TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'documents.sources.read')
        OR app.has_permission(tenant_id, 'documents.sources.admit')
        OR app.has_permission(tenant_id, 'documents.source_rights.review')
        OR token_digest = app.current_upload_token_digest()
        OR app.has_service_job_scope(tenant_id, source_version_id, app.current_job_stage())
    );
CREATE POLICY source_intents_insert ON app.source_upload_intents FOR INSERT TO lms_api_runtime
    WITH CHECK (app.has_permission(tenant_id, 'documents.sources.admit'));
CREATE POLICY source_intents_update ON app.source_upload_intents FOR UPDATE TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'documents.sources.admit')
        OR app.has_permission(tenant_id, 'documents.sources.cancel')
        OR app.has_permission(tenant_id, 'documents.source_rights.review')
        OR token_digest = app.current_upload_token_digest()
        OR app.has_service_job_scope(tenant_id, source_version_id, app.current_job_stage())
    )
    WITH CHECK (
        app.has_permission(tenant_id, 'documents.sources.admit')
        OR app.has_permission(tenant_id, 'documents.sources.cancel')
        OR app.has_permission(tenant_id, 'documents.source_rights.review')
        OR token_digest = app.current_upload_token_digest()
        OR app.has_service_job_scope(tenant_id, source_version_id, app.current_job_stage())
    );

ALTER TABLE app.source_storage_objects ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.source_storage_objects FORCE ROW LEVEL SECURITY;
CREATE POLICY source_objects_select ON app.source_storage_objects FOR SELECT TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'documents.sources.admit')
        OR app.has_permission(tenant_id, 'documents.sources.cancel')
        OR app.has_permission(tenant_id, 'documents.source_rights.review')
        OR app.has_upload_intent_scope(tenant_id, source_version_id)
        OR app.has_service_job_scope(tenant_id, source_version_id, app.current_job_stage())
    );
CREATE POLICY source_objects_insert ON app.source_storage_objects FOR INSERT TO lms_api_runtime
    WITH CHECK (app.has_upload_intent_scope(tenant_id, source_version_id));
CREATE POLICY source_objects_update ON app.source_storage_objects FOR UPDATE TO lms_api_runtime
    USING (app.has_service_job_scope(tenant_id, source_version_id, app.current_job_stage()))
    WITH CHECK (app.has_service_job_scope(tenant_id, source_version_id, app.current_job_stage()));
CREATE POLICY source_objects_worker ON app.source_storage_objects
    FOR SELECT TO lms_worker_runtime
    USING (app.has_service_job_scope(tenant_id, source_version_id, app.current_job_stage()));
CREATE POLICY source_objects_worker_update ON app.source_storage_objects
    FOR UPDATE TO lms_worker_runtime
    USING (app.has_service_job_scope(tenant_id, source_version_id, app.current_job_stage()))
    WITH CHECK (app.has_service_job_scope(tenant_id, source_version_id, app.current_job_stage()));

ALTER TABLE integration.document_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE integration.document_jobs FORCE ROW LEVEL SECURITY;
CREATE POLICY document_jobs_select ON integration.document_jobs FOR SELECT TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'documents.sources.read')
        OR app.has_permission(tenant_id, 'documents.sources.admit')
        OR app.has_permission(tenant_id, 'documents.sources.cancel')
        OR app.has_permission(tenant_id, 'documents.source_rights.review')
        OR app.has_upload_intent_scope(tenant_id, source_version_id)
        OR (id = app.current_job_id() AND stage = app.current_job_stage())
    );
CREATE POLICY document_jobs_insert ON integration.document_jobs FOR INSERT TO lms_api_runtime
    WITH CHECK (
        app.has_permission(tenant_id, 'documents.sources.cancel')
        OR app.has_permission(tenant_id, 'documents.source_rights.review')
        OR app.has_upload_intent_scope(tenant_id, source_version_id)
    );
CREATE POLICY document_jobs_update ON integration.document_jobs FOR UPDATE TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'documents.sources.cancel')
        OR app.has_permission(tenant_id, 'documents.source_rights.review')
        OR (id = app.current_job_id() AND stage = app.current_job_stage())
    )
    WITH CHECK (
        app.has_permission(tenant_id, 'documents.sources.cancel')
        OR app.has_permission(tenant_id, 'documents.source_rights.review')
        OR (id = app.current_job_id() AND stage = app.current_job_stage())
    );
CREATE POLICY document_jobs_worker ON integration.document_jobs
    FOR SELECT TO lms_worker_runtime
    USING (id = app.current_job_id() AND stage = app.current_job_stage());
CREATE POLICY document_jobs_worker_update ON integration.document_jobs
    FOR UPDATE TO lms_worker_runtime
    USING (id = app.current_job_id() AND stage = app.current_job_stage())
    WITH CHECK (id = app.current_job_id() AND stage = app.current_job_stage());

ALTER TABLE integration.document_job_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE integration.document_job_attempts FORCE ROW LEVEL SECURITY;
CREATE POLICY document_attempts_select ON integration.document_job_attempts
    FOR SELECT TO lms_api_runtime
    USING (
        EXISTS (
            SELECT 1 FROM integration.document_jobs job
             WHERE job.id = document_job_attempts.job_id
               AND job.tenant_id = document_job_attempts.tenant_id
               AND (
                    app.has_permission(job.tenant_id, 'documents.sources.read')
                    OR (
                        job.id = app.current_job_id()
                        AND job.stage = app.current_job_stage()
                    )
               )
        )
    );
CREATE POLICY document_attempts_insert ON integration.document_job_attempts
    FOR INSERT TO lms_api_runtime
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM integration.document_jobs job
             WHERE job.id = document_job_attempts.job_id
               AND job.tenant_id = document_job_attempts.tenant_id
               AND job.id = app.current_job_id()
               AND job.stage = app.current_job_stage()
        )
    );
CREATE POLICY document_attempts_update ON integration.document_job_attempts
    FOR UPDATE TO lms_api_runtime
    USING (
        EXISTS (
            SELECT 1 FROM integration.document_jobs job
             WHERE job.id = document_job_attempts.job_id
               AND job.tenant_id = document_job_attempts.tenant_id
               AND job.id = app.current_job_id()
               AND job.stage = app.current_job_stage()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM integration.document_jobs job
             WHERE job.id = document_job_attempts.job_id
               AND job.tenant_id = document_job_attempts.tenant_id
               AND job.id = app.current_job_id()
               AND job.stage = app.current_job_stage()
        )
    );
CREATE POLICY document_attempts_worker ON integration.document_job_attempts
    FOR SELECT TO lms_worker_runtime
    USING (
        EXISTS (
            SELECT 1 FROM integration.document_jobs job
             WHERE job.id = document_job_attempts.job_id
               AND job.tenant_id = document_job_attempts.tenant_id
               AND job.id = app.current_job_id()
               AND job.stage = app.current_job_stage()
        )
    );
CREATE POLICY document_attempts_worker_insert ON integration.document_job_attempts
    FOR INSERT TO lms_worker_runtime
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM integration.document_jobs job
             WHERE job.id = document_job_attempts.job_id
               AND job.tenant_id = document_job_attempts.tenant_id
               AND job.id = app.current_job_id()
               AND job.stage = app.current_job_stage()
        )
    );
CREATE POLICY document_attempts_worker_update ON integration.document_job_attempts
    FOR UPDATE TO lms_worker_runtime
    USING (
        EXISTS (
            SELECT 1 FROM integration.document_jobs job
             WHERE job.id = document_job_attempts.job_id
               AND job.tenant_id = document_job_attempts.tenant_id
               AND job.id = app.current_job_id()
               AND job.stage = app.current_job_stage()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM integration.document_jobs job
             WHERE job.id = document_job_attempts.job_id
               AND job.tenant_id = document_job_attempts.tenant_id
               AND job.id = app.current_job_id()
               AND job.stage = app.current_job_stage()
        )
    );

DROP POLICY idempotency_all ON integration.idempotency_reservations;
CREATE POLICY idempotency_all ON integration.idempotency_reservations
    FOR ALL TO lms_api_runtime
    USING (
        actor_id = app.current_actor_id()
        AND (
            app.has_permission(tenant_id, 'tenancy.invitations.create')
            OR app.has_permission(tenant_id, 'courses.drafts.write')
            OR app.has_permission(tenant_id, 'courses.review')
            OR app.has_permission(tenant_id, 'courses.publish')
            OR app.has_permission(tenant_id, 'documents.sources.admit')
            OR app.has_permission(tenant_id, 'documents.sources.cancel')
            OR app.has_permission(tenant_id, 'documents.source_rights.review')
        )
    )
    WITH CHECK (
        actor_id = app.current_actor_id()
        AND (
            app.has_permission(tenant_id, 'tenancy.invitations.create')
            OR app.has_permission(tenant_id, 'courses.drafts.write')
            OR app.has_permission(tenant_id, 'courses.review')
            OR app.has_permission(tenant_id, 'courses.publish')
            OR app.has_permission(tenant_id, 'documents.sources.admit')
            OR app.has_permission(tenant_id, 'documents.sources.cancel')
            OR app.has_permission(tenant_id, 'documents.source_rights.review')
        )
    );

DROP POLICY audit_insert ON audit.tenant_audit_facts;
CREATE POLICY audit_insert ON audit.tenant_audit_facts FOR INSERT TO lms_api_runtime
    WITH CHECK (
        (tenant_id = app.current_tenant_id() AND (
            app.has_permission(tenant_id, 'tenancy.invitations.create')
            OR app.has_permission(tenant_id, 'tenancy.memberships.update')
            OR app.has_invitation_access(tenant_id)
            OR app.has_permission(tenant_id, 'courses.drafts.write')
            OR app.has_permission(tenant_id, 'courses.review')
            OR app.has_permission(tenant_id, 'courses.publish')
            OR app.has_permission(tenant_id, 'documents.sources.admit')
            OR app.has_permission(tenant_id, 'documents.sources.cancel')
            OR app.has_permission(tenant_id, 'documents.source_rights.review')
        ))
        OR app.has_upload_intent_scope(tenant_id, subject_id)
        OR app.has_service_job_scope(tenant_id, subject_id, app.current_job_stage())
    );
CREATE POLICY audit_documents_worker_insert ON audit.tenant_audit_facts
    FOR INSERT TO lms_worker_runtime
    WITH CHECK (app.has_service_job_scope(tenant_id, subject_id, app.current_job_stage()));

DROP POLICY outbox_insert ON integration.tenant_outbox_facts;
CREATE POLICY outbox_insert ON integration.tenant_outbox_facts FOR INSERT TO lms_api_runtime
    WITH CHECK (
        (tenant_id = app.current_tenant_id() AND (
            app.has_permission(tenant_id, 'tenancy.invitations.create')
            OR app.has_permission(tenant_id, 'tenancy.memberships.update')
            OR app.has_invitation_access(tenant_id)
            OR app.has_permission(tenant_id, 'courses.drafts.write')
            OR app.has_permission(tenant_id, 'courses.review')
            OR app.has_permission(tenant_id, 'courses.publish')
            OR app.has_permission(tenant_id, 'documents.sources.admit')
            OR app.has_permission(tenant_id, 'documents.sources.cancel')
            OR app.has_permission(tenant_id, 'documents.source_rights.review')
        ))
        OR app.has_upload_intent_scope(tenant_id, aggregate_id)
        OR app.has_service_job_scope(tenant_id, aggregate_id, app.current_job_stage())
    );
CREATE POLICY outbox_documents_worker_insert ON integration.tenant_outbox_facts
    FOR INSERT TO lms_worker_runtime
    WITH CHECK (app.has_service_job_scope(tenant_id, aggregate_id, app.current_job_stage()));

GRANT SELECT, INSERT, UPDATE ON app.source_documents, app.source_document_versions,
    app.source_use_authorizations, app.source_upload_intents TO lms_api_runtime;
GRANT SELECT, INSERT ON app.source_rights_declarations TO lms_api_runtime;
GRANT SELECT, INSERT, UPDATE ON app.source_storage_objects,
    integration.document_jobs, integration.document_job_attempts TO lms_api_runtime;

GRANT SELECT, UPDATE ON app.source_document_versions, app.source_storage_objects,
    integration.document_jobs TO lms_worker_runtime;
GRANT SELECT ON app.source_documents, app.source_rights_declarations,
    app.source_use_authorizations, app.source_upload_intents TO lms_worker_runtime;
GRANT SELECT, INSERT, UPDATE ON integration.document_job_attempts TO lms_worker_runtime;
GRANT INSERT ON audit.tenant_audit_facts, integration.tenant_outbox_facts
    TO lms_worker_runtime;
"""


REVERSE_SQL = r"""
REVOKE ALL ON app.source_documents, app.source_document_versions,
    app.source_rights_declarations, app.source_use_authorizations,
    app.source_upload_intents, app.source_storage_objects,
    integration.document_jobs, integration.document_job_attempts FROM lms_api_runtime;
REVOKE ALL ON app.source_documents, app.source_document_versions,
    app.source_rights_declarations, app.source_use_authorizations,
    app.source_upload_intents, app.source_storage_objects,
    integration.document_jobs, integration.document_job_attempts,
    audit.tenant_audit_facts, integration.tenant_outbox_facts FROM lms_worker_runtime;

DROP POLICY IF EXISTS outbox_documents_worker_insert ON integration.tenant_outbox_facts;
DROP POLICY IF EXISTS audit_documents_worker_insert ON audit.tenant_audit_facts;
DROP POLICY IF EXISTS document_attempts_worker_update ON integration.document_job_attempts;
DROP POLICY IF EXISTS document_attempts_worker_insert ON integration.document_job_attempts;
DROP POLICY IF EXISTS document_attempts_worker ON integration.document_job_attempts;
DROP POLICY IF EXISTS document_attempts_update ON integration.document_job_attempts;
DROP POLICY IF EXISTS document_attempts_insert ON integration.document_job_attempts;
DROP POLICY IF EXISTS document_attempts_select ON integration.document_job_attempts;
DROP POLICY IF EXISTS document_jobs_worker_update ON integration.document_jobs;
DROP POLICY IF EXISTS document_jobs_worker ON integration.document_jobs;
DROP POLICY IF EXISTS document_jobs_update ON integration.document_jobs;
DROP POLICY IF EXISTS document_jobs_insert ON integration.document_jobs;
DROP POLICY IF EXISTS document_jobs_select ON integration.document_jobs;
DROP POLICY IF EXISTS source_objects_worker_update ON app.source_storage_objects;
DROP POLICY IF EXISTS source_objects_worker ON app.source_storage_objects;
DROP POLICY IF EXISTS source_objects_update ON app.source_storage_objects;
DROP POLICY IF EXISTS source_objects_insert ON app.source_storage_objects;
DROP POLICY IF EXISTS source_objects_select ON app.source_storage_objects;
DROP POLICY IF EXISTS source_intents_update ON app.source_upload_intents;
DROP POLICY IF EXISTS source_intents_insert ON app.source_upload_intents;
DROP POLICY IF EXISTS source_intents_select ON app.source_upload_intents;
DROP POLICY IF EXISTS source_auth_worker_select ON app.source_use_authorizations;
DROP POLICY IF EXISTS source_auth_update ON app.source_use_authorizations;
DROP POLICY IF EXISTS source_auth_insert ON app.source_use_authorizations;
DROP POLICY IF EXISTS source_auth_select ON app.source_use_authorizations;
DROP POLICY IF EXISTS source_rights_worker_select ON app.source_rights_declarations;
DROP POLICY IF EXISTS source_rights_insert ON app.source_rights_declarations;
DROP POLICY IF EXISTS source_rights_select ON app.source_rights_declarations;
DROP POLICY IF EXISTS source_versions_worker_update ON app.source_document_versions;
DROP POLICY IF EXISTS source_versions_worker ON app.source_document_versions;
DROP POLICY IF EXISTS source_versions_update ON app.source_document_versions;
DROP POLICY IF EXISTS source_versions_insert ON app.source_document_versions;
DROP POLICY IF EXISTS source_versions_select ON app.source_document_versions;
DROP POLICY IF EXISTS source_documents_worker_select ON app.source_documents;
DROP POLICY IF EXISTS source_documents_update ON app.source_documents;
DROP POLICY IF EXISTS source_documents_insert ON app.source_documents;
DROP POLICY IF EXISTS source_documents_select ON app.source_documents;
DROP POLICY IF EXISTS audit_insert ON audit.tenant_audit_facts;
DROP POLICY IF EXISTS outbox_insert ON integration.tenant_outbox_facts;

DROP TRIGGER IF EXISTS document_attempts_immutable ON integration.document_job_attempts;
DROP TRIGGER IF EXISTS document_jobs_lifecycle ON integration.document_jobs;
DROP TRIGGER IF EXISTS source_upload_intents_lifecycle ON app.source_upload_intents;
DROP TRIGGER IF EXISTS source_authorizations_lifecycle ON app.source_use_authorizations;
DROP TRIGGER IF EXISTS source_objects_immutable_observation ON app.source_storage_objects;
DROP TRIGGER IF EXISTS source_versions_lifecycle ON app.source_document_versions;
DROP TRIGGER IF EXISTS source_documents_immutable_identity ON app.source_documents;
DROP TRIGGER IF EXISTS source_rights_immutable ON app.source_rights_declarations;
DROP FUNCTION IF EXISTS integration.enforce_document_attempt_mutation();
DROP FUNCTION IF EXISTS integration.enforce_document_job_mutation();
DROP FUNCTION IF EXISTS app.enforce_source_intent_mutation();
DROP FUNCTION IF EXISTS app.enforce_source_authorization_mutation();
DROP FUNCTION IF EXISTS app.enforce_source_object_mutation();
DROP FUNCTION IF EXISTS app.enforce_source_version_mutation();
DROP FUNCTION IF EXISTS app.enforce_source_document_mutation();
DROP FUNCTION IF EXISTS app.reject_source_rights_mutation();
DROP FUNCTION IF EXISTS app.has_service_job_scope(uuid, uuid, text);
DROP FUNCTION IF EXISTS app.has_upload_intent_scope(uuid, uuid);
DROP FUNCTION IF EXISTS app.current_job_stage();
DROP FUNCTION IF EXISTS app.current_job_id();
DROP FUNCTION IF EXISTS app.current_upload_token_digest();

ALTER TABLE integration.document_job_attempts
    DROP CONSTRAINT IF EXISTS ck_document_attempts_output_hash,
    DROP CONSTRAINT IF EXISTS ck_document_attempts_input_hash,
    DROP CONSTRAINT IF EXISTS ck_document_attempts_observation_object,
    DROP CONSTRAINT IF EXISTS fk_document_attempts_same_tenant_job;
ALTER TABLE integration.document_jobs
    DROP CONSTRAINT IF EXISTS ck_document_jobs_attempt_bounds,
    DROP CONSTRAINT IF EXISTS ck_document_jobs_lease_shape,
    DROP CONSTRAINT IF EXISTS ck_document_jobs_output_hash,
    DROP CONSTRAINT IF EXISTS fk_document_jobs_same_tenant_object,
    DROP CONSTRAINT IF EXISTS fk_document_jobs_same_tenant_version,
    DROP CONSTRAINT IF EXISTS fk_document_jobs_same_tenant_document;
ALTER TABLE app.source_storage_objects
    DROP CONSTRAINT IF EXISTS ck_source_objects_removal_time,
    DROP CONSTRAINT IF EXISTS ck_source_objects_pdf_media,
    DROP CONSTRAINT IF EXISTS ck_source_objects_positive_bytes,
    DROP CONSTRAINT IF EXISTS fk_source_objects_same_tenant_intent,
    DROP CONSTRAINT IF EXISTS fk_source_objects_same_tenant_version,
    DROP CONSTRAINT IF EXISTS fk_source_objects_same_tenant_document;
ALTER TABLE app.source_upload_intents
    DROP CONSTRAINT IF EXISTS ck_source_intents_upload_claim,
    DROP CONSTRAINT IF EXISTS ck_source_intents_checksum,
    DROP CONSTRAINT IF EXISTS ck_source_intents_observation_shape,
    DROP CONSTRAINT IF EXISTS fk_source_intents_same_tenant_authorization,
    DROP CONSTRAINT IF EXISTS fk_source_intents_same_tenant_version,
    DROP CONSTRAINT IF EXISTS fk_source_intents_same_tenant_document;
ALTER TABLE app.source_use_authorizations
    DROP CONSTRAINT IF EXISTS ck_source_auth_decision_shape,
    DROP CONSTRAINT IF EXISTS ck_source_auth_reviewer_separation,
    DROP CONSTRAINT IF EXISTS fk_source_auth_same_tenant_declaration,
    DROP CONSTRAINT IF EXISTS fk_source_auth_same_tenant_version,
    DROP CONSTRAINT IF EXISTS fk_source_auth_same_tenant_document;
ALTER TABLE app.source_rights_declarations
    DROP CONSTRAINT IF EXISTS fk_source_rights_same_tenant_version,
    DROP CONSTRAINT IF EXISTS fk_source_rights_same_tenant_document;
ALTER TABLE app.source_documents
    DROP CONSTRAINT IF EXISTS fk_source_documents_current_version;
ALTER TABLE app.source_document_versions
    DROP CONSTRAINT IF EXISTS ck_source_versions_removal_shape,
    DROP CONSTRAINT IF EXISTS ck_source_versions_admitted_evidence,
    DROP CONSTRAINT IF EXISTS ck_source_versions_rejection_shape,
    DROP CONSTRAINT IF EXISTS fk_source_versions_same_tenant_document;

DROP POLICY IF EXISTS idempotency_all ON integration.idempotency_reservations;
CREATE POLICY idempotency_all ON integration.idempotency_reservations
    FOR ALL TO lms_api_runtime
    USING (
        actor_id = app.current_actor_id()
        AND (
            app.has_permission(tenant_id, 'tenancy.invitations.create')
            OR app.has_permission(tenant_id, 'courses.drafts.write')
            OR app.has_permission(tenant_id, 'courses.review')
            OR app.has_permission(tenant_id, 'courses.publish')
        )
    )
    WITH CHECK (
        actor_id = app.current_actor_id()
        AND (
            app.has_permission(tenant_id, 'tenancy.invitations.create')
            OR app.has_permission(tenant_id, 'courses.drafts.write')
            OR app.has_permission(tenant_id, 'courses.review')
            OR app.has_permission(tenant_id, 'courses.publish')
        )
    );
DROP POLICY IF EXISTS audit_insert ON audit.tenant_audit_facts;
CREATE POLICY audit_insert ON audit.tenant_audit_facts FOR INSERT TO lms_api_runtime
    WITH CHECK (
        tenant_id = app.current_tenant_id()
        AND (
            app.has_permission(tenant_id, 'tenancy.invitations.create')
            OR app.has_permission(tenant_id, 'tenancy.memberships.update')
            OR app.has_invitation_access(tenant_id)
            OR app.has_permission(tenant_id, 'courses.drafts.write')
            OR app.has_permission(tenant_id, 'courses.review')
            OR app.has_permission(tenant_id, 'courses.publish')
        )
    );
DROP POLICY IF EXISTS outbox_insert ON integration.tenant_outbox_facts;
CREATE POLICY outbox_insert ON integration.tenant_outbox_facts FOR INSERT TO lms_api_runtime
    WITH CHECK (
        tenant_id = app.current_tenant_id()
        AND (
            app.has_permission(tenant_id, 'tenancy.invitations.create')
            OR app.has_permission(tenant_id, 'tenancy.memberships.update')
            OR app.has_invitation_access(tenant_id)
            OR app.has_permission(tenant_id, 'courses.drafts.write')
            OR app.has_permission(tenant_id, 'courses.review')
            OR app.has_permission(tenant_id, 'courses.publish')
        )
    );

REVOKE ALL ON FUNCTION app.current_actor_id(), app.current_tenant_id()
    FROM lms_worker_runtime;
REVOKE USAGE ON SCHEMA app, audit, integration FROM lms_worker_runtime;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0001_initial"),
        ("courses", "0003_one_successor"),
    ]
    operations = [
        migrations.RunPython(seed_document_permissions, unseed_document_permissions),
        migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL),
    ]
