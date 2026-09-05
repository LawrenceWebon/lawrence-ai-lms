from __future__ import annotations

import uuid

from django.db import migrations

INGESTION_PERMISSIONS = {
    "documents.ingestion.start": "Start parser-backed source ingestion",
    "documents.ingestion.read": "Read source ingestion status and normalized evidence",
}
ROLE_PERMISSION_CODES = {
    "tenant_admin": tuple(sorted(INGESTION_PERMISSIONS)),
    "instructor": tuple(sorted(INGESTION_PERMISSIONS)),
    "reviewer": (),
    "learner": (),
}


def seed_ingestion_permissions(apps, schema_editor):
    del schema_editor
    Permission = apps.get_model("tenancy", "Permission")
    Role = apps.get_model("tenancy", "Role")
    RolePermission = apps.get_model("tenancy", "RolePermission")
    permissions = {}
    for code, description in INGESTION_PERMISSIONS.items():
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


def unseed_ingestion_permissions(apps, schema_editor):
    del schema_editor
    Permission = apps.get_model("tenancy", "Permission")
    RolePermission = apps.get_model("tenancy", "RolePermission")
    permission_ids = list(
        Permission.objects.filter(code__in=INGESTION_PERMISSIONS).values_list("id", flat=True)
    )
    RolePermission.objects.filter(permission_id__in=permission_ids).delete()
    Permission.objects.filter(id__in=permission_ids).delete()


FORWARD_SQL = r"""
ALTER TABLE integration.document_ingestion_runs OWNER TO lms_object_owner;
ALTER TABLE integration.document_ingestion_attempts OWNER TO lms_object_owner;
ALTER TABLE app.source_artifacts OWNER TO lms_object_owner;
ALTER TABLE app.document_pages OWNER TO lms_object_owner;
ALTER TABLE app.document_elements OWNER TO lms_object_owner;
ALTER TABLE app.document_sections OWNER TO lms_object_owner;
ALTER TABLE app.document_section_elements OWNER TO lms_object_owner;

REVOKE ALL ON integration.document_ingestion_runs,
    integration.document_ingestion_attempts, app.source_artifacts,
    app.document_pages, app.document_elements, app.document_sections,
    app.document_section_elements FROM PUBLIC;

-- Requesters may lock the store authorization while deriving a new operation
-- request, but only reviewers may persist an authorization update.
DROP POLICY IF EXISTS source_auth_update ON app.source_use_authorizations;
CREATE POLICY source_auth_update ON app.source_use_authorizations
    FOR UPDATE TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'documents.source_rights.review')
        OR app.has_permission(tenant_id, 'documents.sources.admit')
    )
    WITH CHECK (app.has_permission(tenant_id, 'documents.source_rights.review'));

ALTER TABLE integration.document_ingestion_runs
    ADD CONSTRAINT fk_ingestion_runs_same_tenant_document
    FOREIGN KEY (tenant_id, source_document_id)
    REFERENCES app.source_documents (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_ingestion_runs_same_tenant_version
    FOREIGN KEY (tenant_id, source_document_id, source_version_id)
    REFERENCES app.source_document_versions (tenant_id, source_document_id, id)
    ON DELETE RESTRICT,
    ADD CONSTRAINT fk_ingestion_runs_same_tenant_object
    FOREIGN KEY (tenant_id, source_version_id, storage_object_id)
    REFERENCES app.source_storage_objects (tenant_id, source_version_id, id)
    ON DELETE RESTRICT,
    ADD CONSTRAINT fk_ingestion_runs_same_tenant_authorization
    FOREIGN KEY (tenant_id, source_version_id, extract_authorization_id)
    REFERENCES app.source_use_authorizations (tenant_id, source_version_id, id)
    ON DELETE RESTRICT;
ALTER TABLE integration.document_ingestion_attempts
    ADD CONSTRAINT fk_ingestion_attempts_same_tenant_run
    FOREIGN KEY (tenant_id, ingestion_run_id)
    REFERENCES integration.document_ingestion_runs (tenant_id, id) ON DELETE RESTRICT;
ALTER TABLE app.source_artifacts
    ADD CONSTRAINT fk_source_artifacts_same_tenant_document
    FOREIGN KEY (tenant_id, source_document_id)
    REFERENCES app.source_documents (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_source_artifacts_same_tenant_version
    FOREIGN KEY (tenant_id, source_document_id, source_version_id)
    REFERENCES app.source_document_versions (tenant_id, source_document_id, id)
    ON DELETE RESTRICT,
    ADD CONSTRAINT fk_source_artifacts_same_tenant_run
    FOREIGN KEY (tenant_id, source_version_id, created_by_run_id)
    REFERENCES integration.document_ingestion_runs (tenant_id, source_version_id, id)
    ON DELETE RESTRICT;
ALTER TABLE app.document_pages
    ADD CONSTRAINT fk_document_pages_same_tenant_document
    FOREIGN KEY (tenant_id, source_document_id)
    REFERENCES app.source_documents (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_document_pages_same_tenant_version
    FOREIGN KEY (tenant_id, source_document_id, source_version_id)
    REFERENCES app.source_document_versions (tenant_id, source_document_id, id)
    ON DELETE RESTRICT,
    ADD CONSTRAINT fk_document_pages_same_tenant_run
    FOREIGN KEY (tenant_id, source_version_id, created_by_run_id)
    REFERENCES integration.document_ingestion_runs (tenant_id, source_version_id, id)
    ON DELETE RESTRICT;
ALTER TABLE app.document_elements
    ADD CONSTRAINT fk_document_elements_same_tenant_document
    FOREIGN KEY (tenant_id, source_document_id)
    REFERENCES app.source_documents (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_document_elements_same_tenant_version
    FOREIGN KEY (tenant_id, source_document_id, source_version_id)
    REFERENCES app.source_document_versions (tenant_id, source_document_id, id)
    ON DELETE RESTRICT,
    ADD CONSTRAINT fk_document_elements_same_tenant_page
    FOREIGN KEY (tenant_id, source_version_id, page_id)
    REFERENCES app.document_pages (tenant_id, source_version_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_document_elements_same_tenant_run
    FOREIGN KEY (tenant_id, source_version_id, created_by_run_id)
    REFERENCES integration.document_ingestion_runs (tenant_id, source_version_id, id)
    ON DELETE RESTRICT;
ALTER TABLE app.document_sections
    ADD CONSTRAINT fk_document_sections_same_tenant_document
    FOREIGN KEY (tenant_id, source_document_id)
    REFERENCES app.source_documents (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_document_sections_same_tenant_version
    FOREIGN KEY (tenant_id, source_document_id, source_version_id)
    REFERENCES app.source_document_versions (tenant_id, source_document_id, id)
    ON DELETE RESTRICT,
    ADD CONSTRAINT fk_document_sections_same_tenant_run
    FOREIGN KEY (tenant_id, source_version_id, created_by_run_id)
    REFERENCES integration.document_ingestion_runs (tenant_id, source_version_id, id)
    ON DELETE RESTRICT;
ALTER TABLE app.document_section_elements
    ADD CONSTRAINT fk_section_elements_same_tenant_version
    FOREIGN KEY (tenant_id, source_version_id)
    REFERENCES app.source_document_versions (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_section_elements_same_tenant_section
    FOREIGN KEY (tenant_id, source_version_id, section_id)
    REFERENCES app.document_sections (tenant_id, source_version_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_section_elements_same_tenant_element
    FOREIGN KEY (tenant_id, source_version_id, element_id)
    REFERENCES app.document_elements (tenant_id, source_version_id, id) ON DELETE RESTRICT;

ALTER TABLE integration.document_ingestion_runs
    ADD CONSTRAINT ck_ingestion_runs_lease_shape CHECK (
        (
            status IN ('claimed', 'extracting', 'normalizing', 'quality_check')
            AND lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL
            AND heartbeat_at IS NOT NULL
        )
        OR (
            status NOT IN ('claimed', 'extracting', 'normalizing', 'quality_check')
            AND lease_owner IS NULL AND lease_expires_at IS NULL
        )
    ),
    ADD CONSTRAINT ck_ingestion_runs_result_shape CHECK (
        (
            status = 'ready_for_generation' AND output_manifest_sha256 IS NOT NULL
            AND reason_code IS NULL
        )
        OR (
            status IN ('retryable', 'failed', 'rights_blocked')
            AND reason_code IS NOT NULL
        )
        OR (
            status IN ('queued', 'claimed', 'extracting', 'normalizing', 'quality_check')
            AND output_manifest_sha256 IS NULL AND reason_code IS NULL
        )
        OR status = 'cancelled'
    ),
    ADD CONSTRAINT ck_ingestion_runs_quality_object CHECK (
        jsonb_typeof(quality_summary) = 'object'
    );
ALTER TABLE integration.document_ingestion_attempts
    ADD CONSTRAINT ck_ingestion_attempts_completion_shape CHECK (
        (outcome = 'running' AND completed_at IS NULL)
        OR (outcome <> 'running' AND completed_at IS NOT NULL)
    ),
    ADD CONSTRAINT ck_ingestion_attempts_observation_object CHECK (
        jsonb_typeof(observation) = 'object'
    );

CREATE OR REPLACE FUNCTION app.has_ingestion_run_scope(
    target_tenant_id uuid,
    target_source_version_id uuid
)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, integration
SET row_security = off
AS $$
    SELECT app.current_job_id() IS NOT NULL
       AND app.current_job_stage() LIKE 'ingestion\_%' ESCAPE '\'
       AND EXISTS (
            SELECT 1
              FROM integration.document_ingestion_runs run
             WHERE run.id = app.current_job_id()
               AND run.tenant_id = target_tenant_id
               AND run.source_version_id = target_source_version_id
       )
$$;
CREATE OR REPLACE FUNCTION app.has_ingestion_event_scope(
    target_tenant_id uuid,
    target_run_id uuid
)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, integration
SET row_security = off
AS $$
    SELECT app.current_job_id() = target_run_id
       AND app.current_job_stage() LIKE 'ingestion\_%' ESCAPE '\'
       AND EXISTS (
            SELECT 1
              FROM integration.document_ingestion_runs run
             WHERE run.id = target_run_id AND run.tenant_id = target_tenant_id
       )
$$;
REVOKE ALL ON FUNCTION app.has_ingestion_run_scope(uuid, uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION app.has_ingestion_event_scope(uuid, uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app.has_ingestion_run_scope(uuid, uuid),
    app.has_ingestion_event_scope(uuid, uuid)
    TO lms_api_runtime, lms_worker_runtime;

CREATE OR REPLACE FUNCTION app.enforce_ingestion_run_mutation()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, app
SET row_security = off
AS $$
DECLARE
    authorization_operation text;
    authorization_status text;
    source_status text;
    object_status text;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'document ingestion runs are retained' USING ERRCODE = '55000';
    END IF;
    IF TG_OP = 'INSERT' THEN
        SELECT auth_row.operation, auth_row.status
          INTO authorization_operation, authorization_status
          FROM app.source_use_authorizations auth_row
         WHERE auth_row.id = NEW.extract_authorization_id
           AND auth_row.tenant_id = NEW.tenant_id
           AND auth_row.source_version_id = NEW.source_version_id;
        SELECT version.admission_status INTO source_status
          FROM app.source_document_versions version
         WHERE version.id = NEW.source_version_id
           AND version.tenant_id = NEW.tenant_id
           AND version.source_document_id = NEW.source_document_id;
        SELECT storage.status INTO object_status
          FROM app.source_storage_objects storage
         WHERE storage.id = NEW.storage_object_id
           AND storage.tenant_id = NEW.tenant_id
           AND storage.source_version_id = NEW.source_version_id;
        IF authorization_operation IS DISTINCT FROM 'extract'
           OR authorization_status IS DISTINCT FROM 'active'
           OR source_status IS DISTINCT FROM 'admitted'
           OR object_status IS DISTINCT FROM 'present' THEN
            RAISE EXCEPTION 'active extraction scope is required' USING ERRCODE = '42501';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id
       OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
       OR NEW.source_document_id IS DISTINCT FROM OLD.source_document_id
       OR NEW.source_version_id IS DISTINCT FROM OLD.source_version_id
       OR NEW.storage_object_id IS DISTINCT FROM OLD.storage_object_id
       OR NEW.extract_authorization_id IS DISTINCT FROM OLD.extract_authorization_id
       OR NEW.requested_by_actor_id IS DISTINCT FROM OLD.requested_by_actor_id
       OR NEW.parser_version IS DISTINCT FROM OLD.parser_version
       OR NEW.configuration_version IS DISTINCT FROM OLD.configuration_version
       OR NEW.locale IS DISTINCT FROM OLD.locale
       OR NEW.input_manifest_sha256 IS DISTINCT FROM OLD.input_manifest_sha256
       OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'document ingestion scope is immutable' USING ERRCODE = '55000';
    END IF;
    IF OLD.status = 'queued' AND NEW.status NOT IN (
        'queued', 'claimed', 'cancelled', 'rights_blocked'
    ) THEN
        RAISE EXCEPTION 'invalid document ingestion transition' USING ERRCODE = '23514';
    ELSIF OLD.status = 'claimed' AND NEW.status NOT IN (
        'claimed', 'extracting', 'retryable', 'failed', 'rights_blocked'
    ) THEN
        RAISE EXCEPTION 'invalid document ingestion transition' USING ERRCODE = '23514';
    ELSIF OLD.status = 'extracting' AND NEW.status NOT IN (
        'extracting', 'normalizing', 'retryable', 'failed', 'rights_blocked'
    ) THEN
        RAISE EXCEPTION 'invalid document ingestion transition' USING ERRCODE = '23514';
    ELSIF OLD.status = 'normalizing' AND NEW.status NOT IN (
        'normalizing', 'quality_check', 'retryable', 'failed', 'rights_blocked'
    ) THEN
        RAISE EXCEPTION 'invalid document ingestion transition' USING ERRCODE = '23514';
    ELSIF OLD.status = 'quality_check' AND NEW.status NOT IN (
        'quality_check', 'ready_for_generation', 'retryable', 'failed', 'rights_blocked'
    ) THEN
        RAISE EXCEPTION 'invalid document ingestion transition' USING ERRCODE = '23514';
    ELSIF OLD.status = 'retryable' AND NEW.status NOT IN (
        'retryable', 'claimed', 'failed', 'cancelled', 'rights_blocked'
    ) THEN
        RAISE EXCEPTION 'invalid document ingestion transition' USING ERRCODE = '23514';
    ELSIF OLD.status IN ('ready_for_generation', 'failed', 'cancelled', 'rights_blocked')
       AND NEW.status <> OLD.status THEN
        RAISE EXCEPTION 'terminal document ingestion run is immutable' USING ERRCODE = '23514';
    END IF;
    IF NEW.status IS DISTINCT FROM OLD.status AND NEW.row_version <> OLD.row_version + 1 THEN
        RAISE EXCEPTION 'document ingestion transition requires next row version'
            USING ERRCODE = '23514';
    END IF;
    IF OLD.status IN ('ready_for_generation', 'failed', 'cancelled', 'rights_blocked')
       AND NEW IS DISTINCT FROM OLD THEN
        RAISE EXCEPTION 'terminal document ingestion evidence is immutable'
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION app.enforce_ingestion_run_mutation() FROM PUBLIC;

CREATE OR REPLACE FUNCTION app.enforce_ingestion_attempt_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'document ingestion attempts are retained' USING ERRCODE = '55000';
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id
       OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
       OR NEW.ingestion_run_id IS DISTINCT FROM OLD.ingestion_run_id
       OR NEW.attempt_number IS DISTINCT FROM OLD.attempt_number
       OR NEW.input_manifest_sha256 IS DISTINCT FROM OLD.input_manifest_sha256
       OR NEW.started_at IS DISTINCT FROM OLD.started_at THEN
        RAISE EXCEPTION 'document ingestion attempt identity is immutable'
            USING ERRCODE = '55000';
    END IF;
    IF OLD.outcome <> 'running' AND NEW IS DISTINCT FROM OLD THEN
        RAISE EXCEPTION 'completed document ingestion attempt is immutable'
            USING ERRCODE = '55000';
    END IF;
    IF OLD.outcome = 'running' AND NEW.outcome NOT IN (
        'running', 'completed', 'retryable', 'failed', 'cancelled', 'rights_blocked'
    ) THEN
        RAISE EXCEPTION 'invalid document ingestion attempt transition'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION app.enforce_ingestion_attempt_mutation() FROM PUBLIC;

CREATE OR REPLACE FUNCTION app.reject_normalized_source_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    RAISE EXCEPTION 'normalized source records are immutable' USING ERRCODE = '55000';
END
$$;
REVOKE ALL ON FUNCTION app.reject_normalized_source_mutation() FROM PUBLIC;

CREATE TRIGGER trg_ingestion_runs_guard
BEFORE INSERT OR UPDATE OR DELETE ON integration.document_ingestion_runs
FOR EACH ROW EXECUTE FUNCTION app.enforce_ingestion_run_mutation();
CREATE TRIGGER trg_ingestion_attempts_guard
BEFORE UPDATE OR DELETE ON integration.document_ingestion_attempts
FOR EACH ROW EXECUTE FUNCTION app.enforce_ingestion_attempt_mutation();
CREATE TRIGGER trg_source_artifacts_immutable
BEFORE UPDATE OR DELETE ON app.source_artifacts
FOR EACH ROW EXECUTE FUNCTION app.reject_normalized_source_mutation();
CREATE TRIGGER trg_document_pages_immutable
BEFORE UPDATE OR DELETE ON app.document_pages
FOR EACH ROW EXECUTE FUNCTION app.reject_normalized_source_mutation();
CREATE TRIGGER trg_document_elements_immutable
BEFORE UPDATE OR DELETE ON app.document_elements
FOR EACH ROW EXECUTE FUNCTION app.reject_normalized_source_mutation();
CREATE TRIGGER trg_document_sections_immutable
BEFORE UPDATE OR DELETE ON app.document_sections
FOR EACH ROW EXECUTE FUNCTION app.reject_normalized_source_mutation();
CREATE TRIGGER trg_document_section_elements_immutable
BEFORE UPDATE OR DELETE ON app.document_section_elements
FOR EACH ROW EXECUTE FUNCTION app.reject_normalized_source_mutation();

ALTER TABLE integration.document_ingestion_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE integration.document_ingestion_runs FORCE ROW LEVEL SECURITY;
CREATE POLICY ingestion_runs_api_select ON integration.document_ingestion_runs
    FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'documents.ingestion.read'));
CREATE POLICY ingestion_runs_api_insert ON integration.document_ingestion_runs
    FOR INSERT TO lms_api_runtime
    WITH CHECK (app.has_permission(tenant_id, 'documents.ingestion.start'));
CREATE POLICY ingestion_runs_worker_select ON integration.document_ingestion_runs
    FOR SELECT TO lms_worker_runtime
    USING (app.has_ingestion_event_scope(tenant_id, id));
CREATE POLICY ingestion_runs_worker_update ON integration.document_ingestion_runs
    FOR UPDATE TO lms_worker_runtime
    USING (app.has_ingestion_event_scope(tenant_id, id))
    WITH CHECK (app.has_ingestion_event_scope(tenant_id, id));

ALTER TABLE integration.document_ingestion_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE integration.document_ingestion_attempts FORCE ROW LEVEL SECURITY;
CREATE POLICY ingestion_attempts_api_select ON integration.document_ingestion_attempts
    FOR SELECT TO lms_api_runtime
    USING (
        EXISTS (
            SELECT 1 FROM integration.document_ingestion_runs run
             WHERE run.id = document_ingestion_attempts.ingestion_run_id
               AND run.tenant_id = document_ingestion_attempts.tenant_id
               AND app.has_permission(run.tenant_id, 'documents.ingestion.read')
        )
    );
CREATE POLICY ingestion_attempts_worker_select ON integration.document_ingestion_attempts
    FOR SELECT TO lms_worker_runtime
    USING (app.has_ingestion_event_scope(tenant_id, ingestion_run_id));
CREATE POLICY ingestion_attempts_worker_insert ON integration.document_ingestion_attempts
    FOR INSERT TO lms_worker_runtime
    WITH CHECK (app.has_ingestion_event_scope(tenant_id, ingestion_run_id));
CREATE POLICY ingestion_attempts_worker_update ON integration.document_ingestion_attempts
    FOR UPDATE TO lms_worker_runtime
    USING (app.has_ingestion_event_scope(tenant_id, ingestion_run_id))
    WITH CHECK (app.has_ingestion_event_scope(tenant_id, ingestion_run_id));

ALTER TABLE app.source_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.source_artifacts FORCE ROW LEVEL SECURITY;
CREATE POLICY source_artifacts_api_select ON app.source_artifacts FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'documents.ingestion.read'));
CREATE POLICY source_artifacts_worker_select ON app.source_artifacts
    FOR SELECT TO lms_worker_runtime
    USING (app.has_ingestion_run_scope(tenant_id, source_version_id));
CREATE POLICY source_artifacts_worker_insert ON app.source_artifacts
    FOR INSERT TO lms_worker_runtime
    WITH CHECK (
        created_by_run_id = app.current_job_id()
        AND app.has_ingestion_run_scope(tenant_id, source_version_id)
    );

ALTER TABLE app.document_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.document_pages FORCE ROW LEVEL SECURITY;
CREATE POLICY document_pages_api_select ON app.document_pages FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'documents.ingestion.read'));
CREATE POLICY document_pages_worker_select ON app.document_pages FOR SELECT TO lms_worker_runtime
    USING (app.has_ingestion_run_scope(tenant_id, source_version_id));
CREATE POLICY document_pages_worker_insert ON app.document_pages FOR INSERT TO lms_worker_runtime
    WITH CHECK (
        created_by_run_id = app.current_job_id()
        AND app.has_ingestion_run_scope(tenant_id, source_version_id)
    );

ALTER TABLE app.document_elements ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.document_elements FORCE ROW LEVEL SECURITY;
CREATE POLICY document_elements_api_select ON app.document_elements FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'documents.ingestion.read'));
CREATE POLICY document_elements_worker_select ON app.document_elements
    FOR SELECT TO lms_worker_runtime
    USING (app.has_ingestion_run_scope(tenant_id, source_version_id));
CREATE POLICY document_elements_worker_insert ON app.document_elements
    FOR INSERT TO lms_worker_runtime
    WITH CHECK (
        created_by_run_id = app.current_job_id()
        AND app.has_ingestion_run_scope(tenant_id, source_version_id)
    );

ALTER TABLE app.document_sections ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.document_sections FORCE ROW LEVEL SECURITY;
CREATE POLICY document_sections_api_select ON app.document_sections FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'documents.ingestion.read'));
CREATE POLICY document_sections_worker_select ON app.document_sections
    FOR SELECT TO lms_worker_runtime
    USING (app.has_ingestion_run_scope(tenant_id, source_version_id));
CREATE POLICY document_sections_worker_insert ON app.document_sections
    FOR INSERT TO lms_worker_runtime
    WITH CHECK (
        created_by_run_id = app.current_job_id()
        AND app.has_ingestion_run_scope(tenant_id, source_version_id)
    );

ALTER TABLE app.document_section_elements ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.document_section_elements FORCE ROW LEVEL SECURITY;
CREATE POLICY section_elements_api_select ON app.document_section_elements
    FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'documents.ingestion.read'));
CREATE POLICY section_elements_worker_select ON app.document_section_elements
    FOR SELECT TO lms_worker_runtime
    USING (app.has_ingestion_run_scope(tenant_id, source_version_id));
CREATE POLICY section_elements_worker_insert ON app.document_section_elements
    FOR INSERT TO lms_worker_runtime
    WITH CHECK (app.has_ingestion_run_scope(tenant_id, source_version_id));

CREATE POLICY source_documents_ingestion_worker ON app.source_documents
    FOR SELECT TO lms_worker_runtime
    USING (
        EXISTS (
            SELECT 1 FROM integration.document_ingestion_runs run
             WHERE run.id = app.current_job_id()
               AND run.tenant_id = source_documents.tenant_id
               AND run.source_document_id = source_documents.id
               AND app.current_job_stage() LIKE 'ingestion\_%' ESCAPE '\'
        )
    );
CREATE POLICY source_versions_ingestion_worker ON app.source_document_versions
    FOR SELECT TO lms_worker_runtime
    USING (app.has_ingestion_run_scope(tenant_id, id));
CREATE POLICY source_rights_ingestion_worker ON app.source_rights_declarations
    FOR SELECT TO lms_worker_runtime
    USING (app.has_ingestion_run_scope(tenant_id, source_version_id));
CREATE POLICY source_auth_ingestion_worker ON app.source_use_authorizations
    FOR SELECT TO lms_worker_runtime
    USING (app.has_ingestion_run_scope(tenant_id, source_version_id));
CREATE POLICY source_auth_ingestion_worker_insert ON app.source_use_authorizations
    FOR INSERT TO lms_worker_runtime
    WITH CHECK (
        operation = 'ocr' AND status = 'requested'
        AND app.has_ingestion_run_scope(tenant_id, source_version_id)
        AND requested_by_actor_id = (
            SELECT run.requested_by_actor_id
              FROM integration.document_ingestion_runs run
             WHERE run.id = app.current_job_id()
               AND run.tenant_id = source_use_authorizations.tenant_id
               AND run.source_version_id = source_use_authorizations.source_version_id
        )
    );
CREATE POLICY source_objects_ingestion_worker ON app.source_storage_objects
    FOR SELECT TO lms_worker_runtime
    USING (app.has_ingestion_run_scope(tenant_id, source_version_id));

CREATE POLICY idempotency_ingestion_api ON integration.idempotency_reservations
    FOR ALL TO lms_api_runtime
    USING (
        actor_id = app.current_actor_id()
        AND app.has_permission(tenant_id, 'documents.ingestion.start')
    )
    WITH CHECK (
        actor_id = app.current_actor_id()
        AND app.has_permission(tenant_id, 'documents.ingestion.start')
    );
CREATE POLICY audit_ingestion_api_insert ON audit.tenant_audit_facts
    FOR INSERT TO lms_api_runtime
    WITH CHECK (
        tenant_id = app.current_tenant_id()
        AND app.has_permission(tenant_id, 'documents.ingestion.start')
    );
CREATE POLICY outbox_ingestion_api_insert ON integration.tenant_outbox_facts
    FOR INSERT TO lms_api_runtime
    WITH CHECK (
        tenant_id = app.current_tenant_id()
        AND app.has_permission(tenant_id, 'documents.ingestion.start')
    );
CREATE POLICY audit_ingestion_worker_insert ON audit.tenant_audit_facts
    FOR INSERT TO lms_worker_runtime
    WITH CHECK (app.has_ingestion_event_scope(tenant_id, subject_id));
CREATE POLICY outbox_ingestion_worker_insert ON integration.tenant_outbox_facts
    FOR INSERT TO lms_worker_runtime
    WITH CHECK (app.has_ingestion_event_scope(tenant_id, aggregate_id));

GRANT SELECT, INSERT ON integration.document_ingestion_runs TO lms_api_runtime;
GRANT SELECT ON integration.document_ingestion_attempts, app.source_artifacts,
    app.document_pages, app.document_elements, app.document_sections,
    app.document_section_elements TO lms_api_runtime;
GRANT SELECT, UPDATE ON integration.document_ingestion_runs TO lms_worker_runtime;
GRANT SELECT, INSERT, UPDATE ON integration.document_ingestion_attempts
    TO lms_worker_runtime;
GRANT SELECT, INSERT ON app.source_artifacts, app.document_pages,
    app.document_elements, app.document_sections, app.document_section_elements
    TO lms_worker_runtime;
GRANT INSERT ON app.source_use_authorizations TO lms_worker_runtime;
"""


REVERSE_SQL = r"""
REVOKE ALL ON integration.document_ingestion_runs,
    integration.document_ingestion_attempts, app.source_artifacts,
    app.document_pages, app.document_elements, app.document_sections,
    app.document_section_elements FROM lms_api_runtime, lms_worker_runtime;
REVOKE INSERT ON app.source_use_authorizations FROM lms_worker_runtime;

DROP POLICY IF EXISTS source_auth_update ON app.source_use_authorizations;
CREATE POLICY source_auth_update ON app.source_use_authorizations
    FOR UPDATE TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'documents.source_rights.review'))
    WITH CHECK (app.has_permission(tenant_id, 'documents.source_rights.review'));

DROP POLICY IF EXISTS outbox_ingestion_worker_insert ON integration.tenant_outbox_facts;
DROP POLICY IF EXISTS audit_ingestion_worker_insert ON audit.tenant_audit_facts;
DROP POLICY IF EXISTS outbox_ingestion_api_insert ON integration.tenant_outbox_facts;
DROP POLICY IF EXISTS audit_ingestion_api_insert ON audit.tenant_audit_facts;
DROP POLICY IF EXISTS idempotency_ingestion_api ON integration.idempotency_reservations;
DROP POLICY IF EXISTS source_objects_ingestion_worker ON app.source_storage_objects;
DROP POLICY IF EXISTS source_auth_ingestion_worker ON app.source_use_authorizations;
DROP POLICY IF EXISTS source_auth_ingestion_worker_insert ON app.source_use_authorizations;
DROP POLICY IF EXISTS source_rights_ingestion_worker ON app.source_rights_declarations;
DROP POLICY IF EXISTS source_versions_ingestion_worker ON app.source_document_versions;
DROP POLICY IF EXISTS source_documents_ingestion_worker ON app.source_documents;
DROP POLICY IF EXISTS section_elements_worker_insert ON app.document_section_elements;
DROP POLICY IF EXISTS section_elements_worker_select ON app.document_section_elements;
DROP POLICY IF EXISTS section_elements_api_select ON app.document_section_elements;
DROP POLICY IF EXISTS document_sections_worker_insert ON app.document_sections;
DROP POLICY IF EXISTS document_sections_worker_select ON app.document_sections;
DROP POLICY IF EXISTS document_sections_api_select ON app.document_sections;
DROP POLICY IF EXISTS document_elements_worker_insert ON app.document_elements;
DROP POLICY IF EXISTS document_elements_worker_select ON app.document_elements;
DROP POLICY IF EXISTS document_elements_api_select ON app.document_elements;
DROP POLICY IF EXISTS document_pages_worker_insert ON app.document_pages;
DROP POLICY IF EXISTS document_pages_worker_select ON app.document_pages;
DROP POLICY IF EXISTS document_pages_api_select ON app.document_pages;
DROP POLICY IF EXISTS source_artifacts_worker_insert ON app.source_artifacts;
DROP POLICY IF EXISTS source_artifacts_worker_select ON app.source_artifacts;
DROP POLICY IF EXISTS source_artifacts_api_select ON app.source_artifacts;
DROP POLICY IF EXISTS ingestion_attempts_worker_update ON integration.document_ingestion_attempts;
DROP POLICY IF EXISTS ingestion_attempts_worker_insert ON integration.document_ingestion_attempts;
DROP POLICY IF EXISTS ingestion_attempts_worker_select ON integration.document_ingestion_attempts;
DROP POLICY IF EXISTS ingestion_attempts_api_select ON integration.document_ingestion_attempts;
DROP POLICY IF EXISTS ingestion_runs_worker_update ON integration.document_ingestion_runs;
DROP POLICY IF EXISTS ingestion_runs_worker_select ON integration.document_ingestion_runs;
DROP POLICY IF EXISTS ingestion_runs_api_insert ON integration.document_ingestion_runs;
DROP POLICY IF EXISTS ingestion_runs_api_select ON integration.document_ingestion_runs;

DROP TRIGGER IF EXISTS trg_document_section_elements_immutable
    ON app.document_section_elements;
DROP TRIGGER IF EXISTS trg_document_sections_immutable ON app.document_sections;
DROP TRIGGER IF EXISTS trg_document_elements_immutable ON app.document_elements;
DROP TRIGGER IF EXISTS trg_document_pages_immutable ON app.document_pages;
DROP TRIGGER IF EXISTS trg_source_artifacts_immutable ON app.source_artifacts;
DROP TRIGGER IF EXISTS trg_ingestion_attempts_guard
    ON integration.document_ingestion_attempts;
DROP TRIGGER IF EXISTS trg_ingestion_runs_guard ON integration.document_ingestion_runs;
DROP FUNCTION IF EXISTS app.reject_normalized_source_mutation();
DROP FUNCTION IF EXISTS app.enforce_ingestion_attempt_mutation();
DROP FUNCTION IF EXISTS app.enforce_ingestion_run_mutation();
DROP FUNCTION IF EXISTS app.has_ingestion_event_scope(uuid, uuid);
DROP FUNCTION IF EXISTS app.has_ingestion_run_scope(uuid, uuid);

ALTER TABLE app.document_section_elements
    DROP CONSTRAINT IF EXISTS fk_section_elements_same_tenant_element,
    DROP CONSTRAINT IF EXISTS fk_section_elements_same_tenant_section,
    DROP CONSTRAINT IF EXISTS fk_section_elements_same_tenant_version;
ALTER TABLE app.document_sections
    DROP CONSTRAINT IF EXISTS fk_document_sections_same_tenant_run,
    DROP CONSTRAINT IF EXISTS fk_document_sections_same_tenant_version,
    DROP CONSTRAINT IF EXISTS fk_document_sections_same_tenant_document;
ALTER TABLE app.document_elements
    DROP CONSTRAINT IF EXISTS fk_document_elements_same_tenant_run,
    DROP CONSTRAINT IF EXISTS fk_document_elements_same_tenant_page,
    DROP CONSTRAINT IF EXISTS fk_document_elements_same_tenant_version,
    DROP CONSTRAINT IF EXISTS fk_document_elements_same_tenant_document;
ALTER TABLE app.document_pages
    DROP CONSTRAINT IF EXISTS fk_document_pages_same_tenant_run,
    DROP CONSTRAINT IF EXISTS fk_document_pages_same_tenant_version,
    DROP CONSTRAINT IF EXISTS fk_document_pages_same_tenant_document;
ALTER TABLE app.source_artifacts
    DROP CONSTRAINT IF EXISTS fk_source_artifacts_same_tenant_run,
    DROP CONSTRAINT IF EXISTS fk_source_artifacts_same_tenant_version,
    DROP CONSTRAINT IF EXISTS fk_source_artifacts_same_tenant_document;
ALTER TABLE integration.document_ingestion_attempts
    DROP CONSTRAINT IF EXISTS ck_ingestion_attempts_observation_object,
    DROP CONSTRAINT IF EXISTS ck_ingestion_attempts_completion_shape,
    DROP CONSTRAINT IF EXISTS fk_ingestion_attempts_same_tenant_run;
ALTER TABLE integration.document_ingestion_runs
    DROP CONSTRAINT IF EXISTS ck_ingestion_runs_quality_object,
    DROP CONSTRAINT IF EXISTS ck_ingestion_runs_result_shape,
    DROP CONSTRAINT IF EXISTS ck_ingestion_runs_lease_shape,
    DROP CONSTRAINT IF EXISTS fk_ingestion_runs_same_tenant_authorization,
    DROP CONSTRAINT IF EXISTS fk_ingestion_runs_same_tenant_object,
    DROP CONSTRAINT IF EXISTS fk_ingestion_runs_same_tenant_version,
    DROP CONSTRAINT IF EXISTS fk_ingestion_runs_same_tenant_document;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0004_ingestion_tenant_keys"),
        ("tenancy", "0002_secure_invitation_bootstrap"),
    ]

    operations = [
        migrations.RunPython(seed_ingestion_permissions, unseed_ingestion_permissions),
        migrations.RunSQL(FORWARD_SQL, REVERSE_SQL),
    ]
