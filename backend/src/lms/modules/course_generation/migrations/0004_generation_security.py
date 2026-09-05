from __future__ import annotations

import uuid

from django.db import migrations

GENERATION_PERMISSIONS = {
    "course_generation.runs.create": "Start structured course generation",
    "course_generation.runs.read": "Read structured generation review packages",
    "course_generation.blueprints.review": "Approve or reject generation blueprints",
    "course_generation.drafts.canonicalize": "Canonicalize a reviewed generation revision",
}
ROLE_PERMISSION_CODES = {
    "tenant_admin": tuple(sorted(GENERATION_PERMISSIONS)),
    "instructor": tuple(sorted(GENERATION_PERMISSIONS)),
    "reviewer": (
        "course_generation.blueprints.review",
        "course_generation.runs.read",
    ),
    "learner": (),
}


def seed_generation_permissions(apps, schema_editor):
    del schema_editor
    Permission = apps.get_model("tenancy", "Permission")
    Role = apps.get_model("tenancy", "Role")
    RolePermission = apps.get_model("tenancy", "RolePermission")
    permissions = {}
    for code, description in GENERATION_PERMISSIONS.items():
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


def unseed_generation_permissions(apps, schema_editor):
    del schema_editor
    Permission = apps.get_model("tenancy", "Permission")
    RolePermission = apps.get_model("tenancy", "RolePermission")
    permission_ids = list(
        Permission.objects.filter(code__in=GENERATION_PERMISSIONS).values_list("id", flat=True)
    )
    RolePermission.objects.filter(permission_id__in=permission_ids).delete()
    Permission.objects.filter(id__in=permission_ids).delete()


FORWARD_SQL = r"""
ALTER TABLE integration.course_generation_runs OWNER TO lms_object_owner;
ALTER TABLE integration.course_generation_attempts OWNER TO lms_object_owner;
ALTER TABLE integration.course_generation_snapshots OWNER TO lms_object_owner;
ALTER TABLE app.course_generation_blueprints OWNER TO lms_object_owner;
ALTER TABLE app.course_generation_blueprint_items OWNER TO lms_object_owner;
ALTER TABLE app.generated_lesson_artifacts OWNER TO lms_object_owner;
ALTER TABLE app.course_generation_source_edges OWNER TO lms_object_owner;
ALTER TABLE audit.course_generation_blueprint_decisions OWNER TO lms_object_owner;
ALTER TABLE audit.course_generation_rejections OWNER TO lms_object_owner;

REVOKE ALL ON integration.course_generation_runs,
    integration.course_generation_attempts,
    integration.course_generation_snapshots,
    app.course_generation_blueprints,
    app.course_generation_blueprint_items,
    app.generated_lesson_artifacts,
    app.course_generation_source_edges,
    audit.course_generation_blueprint_decisions,
    audit.course_generation_rejections FROM PUBLIC;

ALTER TABLE integration.course_generation_runs
    ADD CONSTRAINT fk_generation_runs_same_tenant_document
    FOREIGN KEY (tenant_id, source_document_id)
    REFERENCES app.source_documents (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_generation_runs_same_tenant_version
    FOREIGN KEY (tenant_id, source_document_id, source_version_id)
    REFERENCES app.source_document_versions (tenant_id, source_document_id, id)
    ON DELETE RESTRICT,
    ADD CONSTRAINT fk_generation_runs_same_tenant_ingestion
    FOREIGN KEY (tenant_id, source_version_id, ingestion_run_id)
    REFERENCES integration.document_ingestion_runs (tenant_id, source_version_id, id)
    ON DELETE RESTRICT,
    ADD CONSTRAINT fk_generation_runs_same_tenant_authorization
    FOREIGN KEY (tenant_id, source_version_id, generate_authorization_id)
    REFERENCES app.source_use_authorizations (tenant_id, source_version_id, id)
    ON DELETE RESTRICT,
    ADD CONSTRAINT fk_generation_runs_same_tenant_superseded
    FOREIGN KEY (tenant_id, supersedes_run_id)
    REFERENCES integration.course_generation_runs (tenant_id, id) ON DELETE RESTRICT;
ALTER TABLE integration.course_generation_attempts
    ADD CONSTRAINT fk_generation_attempts_same_tenant_run
    FOREIGN KEY (tenant_id, generation_run_id)
    REFERENCES integration.course_generation_runs (tenant_id, id) ON DELETE RESTRICT;
ALTER TABLE integration.course_generation_snapshots
    ADD CONSTRAINT fk_generation_snapshots_same_tenant_run
    FOREIGN KEY (tenant_id, generation_run_id)
    REFERENCES integration.course_generation_runs (tenant_id, id) ON DELETE RESTRICT;
ALTER TABLE app.course_generation_blueprints
    ADD CONSTRAINT fk_generation_blueprints_same_tenant_run
    FOREIGN KEY (tenant_id, generation_run_id)
    REFERENCES integration.course_generation_runs (tenant_id, id) ON DELETE RESTRICT;
ALTER TABLE app.course_generation_blueprint_items
    ADD CONSTRAINT fk_generation_items_same_tenant_run
    FOREIGN KEY (tenant_id, generation_run_id)
    REFERENCES integration.course_generation_runs (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_generation_items_same_tenant_blueprint
    FOREIGN KEY (tenant_id, generation_run_id, blueprint_id)
    REFERENCES app.course_generation_blueprints (tenant_id, generation_run_id, id)
    ON DELETE RESTRICT,
    ADD CONSTRAINT fk_generation_items_same_tenant_parent
    FOREIGN KEY (tenant_id, generation_run_id, parent_id)
    REFERENCES app.course_generation_blueprint_items (tenant_id, generation_run_id, id)
    ON DELETE RESTRICT,
    ADD CONSTRAINT fk_generation_items_same_tenant_version
    FOREIGN KEY (tenant_id, source_version_id)
    REFERENCES app.source_document_versions (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_generation_items_same_tenant_section
    FOREIGN KEY (tenant_id, source_version_id, source_section_id)
    REFERENCES app.document_sections (tenant_id, source_version_id, id) ON DELETE RESTRICT;
ALTER TABLE app.generated_lesson_artifacts
    ADD CONSTRAINT fk_generated_lessons_same_tenant_run
    FOREIGN KEY (tenant_id, generation_run_id)
    REFERENCES integration.course_generation_runs (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_generated_lessons_same_tenant_item
    FOREIGN KEY (tenant_id, generation_run_id, blueprint_item_id)
    REFERENCES app.course_generation_blueprint_items (tenant_id, generation_run_id, id)
    ON DELETE RESTRICT,
    ADD CONSTRAINT fk_generated_lessons_same_tenant_version
    FOREIGN KEY (tenant_id, source_version_id)
    REFERENCES app.source_document_versions (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_generated_lessons_same_tenant_section
    FOREIGN KEY (tenant_id, source_version_id, source_section_id)
    REFERENCES app.document_sections (tenant_id, source_version_id, id) ON DELETE RESTRICT;
ALTER TABLE app.course_generation_source_edges
    ADD CONSTRAINT fk_generation_edges_same_tenant_run
    FOREIGN KEY (tenant_id, generation_run_id)
    REFERENCES integration.course_generation_runs (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_generation_edges_same_tenant_version
    FOREIGN KEY (tenant_id, source_version_id)
    REFERENCES app.source_document_versions (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_generation_edges_same_tenant_section
    FOREIGN KEY (tenant_id, source_version_id, source_section_id)
    REFERENCES app.document_sections (tenant_id, source_version_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_generation_edges_same_tenant_item
    FOREIGN KEY (tenant_id, generation_run_id, blueprint_item_id)
    REFERENCES app.course_generation_blueprint_items (tenant_id, generation_run_id, id)
    ON DELETE RESTRICT,
    ADD CONSTRAINT fk_generation_edges_same_tenant_artifact
    FOREIGN KEY (tenant_id, generation_run_id, generated_artifact_id)
    REFERENCES app.generated_lesson_artifacts (tenant_id, generation_run_id, id)
    ON DELETE RESTRICT;
ALTER TABLE audit.course_generation_blueprint_decisions
    ADD CONSTRAINT fk_generation_decisions_same_tenant_run
    FOREIGN KEY (tenant_id, generation_run_id)
    REFERENCES integration.course_generation_runs (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_generation_decisions_same_tenant_blueprint
    FOREIGN KEY (tenant_id, generation_run_id, blueprint_id)
    REFERENCES app.course_generation_blueprints (tenant_id, generation_run_id, id)
    ON DELETE RESTRICT;
ALTER TABLE audit.course_generation_rejections
    ADD CONSTRAINT fk_generation_rejections_same_tenant_run
    FOREIGN KEY (tenant_id, generation_run_id)
    REFERENCES integration.course_generation_runs (tenant_id, id) ON DELETE RESTRICT;

ALTER TABLE integration.course_generation_runs
    ADD CONSTRAINT ck_generation_runs_lease_shape CHECK (
        (
            status IN ('planning', 'generating')
            AND lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL
            AND heartbeat_at IS NOT NULL
        )
        OR (
            status NOT IN ('planning', 'generating')
            AND lease_owner IS NULL AND lease_expires_at IS NULL
        )
    ),
    ADD CONSTRAINT ck_generation_runs_result_shape CHECK (
        (
            status IN ('queued', 'planning')
            AND blueprint_content_sha256 IS NULL
            AND output_manifest_sha256 IS NULL AND reason_code IS NULL
        )
        OR (
            status IN ('blueprint_review', 'generation_queued', 'generating')
            AND blueprint_content_sha256 IS NOT NULL
            AND output_manifest_sha256 IS NULL AND reason_code IS NULL
        )
        OR (
            status IN ('review_ready', 'canonicalized')
            AND blueprint_content_sha256 IS NOT NULL
            AND output_manifest_sha256 IS NOT NULL AND reason_code IS NULL
        )
        OR (
            status = 'rejected' AND blueprint_content_sha256 IS NOT NULL
            AND reason_code IS NOT NULL
        )
        OR (
            status IN ('retryable', 'failed', 'rights_blocked')
            AND reason_code IS NOT NULL
        )
    );
ALTER TABLE integration.course_generation_attempts
    ADD CONSTRAINT ck_generation_attempts_stage CHECK (
        stage IN ('planning', 'generating')
    ),
    ADD CONSTRAINT ck_generation_attempts_completion_shape CHECK (
        (outcome = 'running' AND completed_at IS NULL)
        OR (outcome <> 'running' AND completed_at IS NOT NULL)
    ),
    ADD CONSTRAINT ck_generation_attempts_observation_object CHECK (
        jsonb_typeof(observation) = 'object'
    );
ALTER TABLE integration.course_generation_snapshots
    ADD CONSTRAINT ck_generation_snapshot_metadata_object CHECK (
        jsonb_typeof(metadata) = 'object'
    );
ALTER TABLE app.course_generation_blueprints
    ADD CONSTRAINT ck_generation_blueprint_projection_object CHECK (
        jsonb_typeof(projection) = 'object'
    ),
    ADD CONSTRAINT ck_generation_blueprint_prerequisites_array CHECK (
        jsonb_typeof(prerequisites) = 'array'
    ),
    ADD CONSTRAINT ck_generation_blueprint_outcomes_array CHECK (
        jsonb_typeof(learning_outcomes) = 'array'
    );
ALTER TABLE app.generated_lesson_artifacts
    ADD CONSTRAINT ck_generated_lesson_document_object CHECK (
        jsonb_typeof(document) = 'object'
    );

CREATE OR REPLACE FUNCTION app.has_generation_event_scope(
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
       AND app.current_job_stage() LIKE 'generation\_%' ESCAPE '\'
       AND EXISTS (
            SELECT 1 FROM integration.course_generation_runs run
             WHERE run.id = target_run_id AND run.tenant_id = target_tenant_id
       )
$$;
CREATE OR REPLACE FUNCTION app.has_generation_source_scope(
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
       AND app.current_job_stage() LIKE 'generation\_%' ESCAPE '\'
       AND EXISTS (
            SELECT 1 FROM integration.course_generation_runs run
             WHERE run.id = app.current_job_id()
               AND run.tenant_id = target_tenant_id
               AND run.source_version_id = target_source_version_id
       )
$$;
REVOKE ALL ON FUNCTION app.has_generation_event_scope(uuid, uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION app.has_generation_source_scope(uuid, uuid) FROM PUBLIC;

CREATE OR REPLACE FUNCTION app.has_generation_canonicalization_evidence(
    p_tenant_id uuid,
    p_generation_run_id uuid,
    p_output_manifest_sha256 text
)
RETURNS boolean
LANGUAGE sql
STABLE
SET search_path = pg_catalog
AS $$
    SELECT false
$$;
REVOKE ALL ON FUNCTION app.has_generation_canonicalization_evidence(uuid, uuid, text)
    FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app.has_generation_event_scope(uuid, uuid),
    app.has_generation_source_scope(uuid, uuid)
    TO lms_api_runtime, lms_worker_runtime;

CREATE OR REPLACE FUNCTION app.enforce_generation_run_mutation()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, app, integration, audit
SET row_security = off
AS $$
DECLARE
    authorization_operation text;
    authorization_status text;
    authorization_valid_from timestamptz;
    authorization_valid_until timestamptz;
    source_status text;
    ingestion_status text;
    current_version_id uuid;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'course generation runs are retained' USING ERRCODE = '55000';
    END IF;
    IF TG_OP = 'INSERT' THEN
        SELECT auth_row.operation, auth_row.status,
               auth_row.valid_from, auth_row.valid_until
          INTO authorization_operation, authorization_status,
               authorization_valid_from, authorization_valid_until
          FROM app.source_use_authorizations auth_row
         WHERE auth_row.id = NEW.generate_authorization_id
           AND auth_row.tenant_id = NEW.tenant_id
           AND auth_row.source_version_id = NEW.source_version_id;
        SELECT version.admission_status INTO source_status
          FROM app.source_document_versions version
         WHERE version.id = NEW.source_version_id
           AND version.tenant_id = NEW.tenant_id
           AND version.source_document_id = NEW.source_document_id;
        SELECT document.current_version_id INTO current_version_id
          FROM app.source_documents document
         WHERE document.id = NEW.source_document_id
           AND document.tenant_id = NEW.tenant_id;
        SELECT ingestion.status INTO ingestion_status
          FROM integration.document_ingestion_runs ingestion
         WHERE ingestion.id = NEW.ingestion_run_id
           AND ingestion.tenant_id = NEW.tenant_id
           AND ingestion.source_version_id = NEW.source_version_id;
        IF authorization_operation IS DISTINCT FROM 'generate'
           OR authorization_status IS DISTINCT FROM 'active'
           OR authorization_valid_from IS NULL
           OR authorization_valid_from > statement_timestamp()
           OR (
                authorization_valid_until IS NOT NULL
                AND authorization_valid_until <= statement_timestamp()
           )
           OR source_status IS DISTINCT FROM 'admitted'
           OR current_version_id IS DISTINCT FROM NEW.source_version_id
           OR ingestion_status IS DISTINCT FROM 'ready_for_generation' THEN
            RAISE EXCEPTION 'active generation scope is required' USING ERRCODE = '42501';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id
       OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
       OR NEW.source_document_id IS DISTINCT FROM OLD.source_document_id
       OR NEW.source_version_id IS DISTINCT FROM OLD.source_version_id
       OR NEW.ingestion_run_id IS DISTINCT FROM OLD.ingestion_run_id
       OR NEW.generate_authorization_id IS DISTINCT FROM OLD.generate_authorization_id
       OR NEW.supersedes_run_id IS DISTINCT FROM OLD.supersedes_run_id
       OR NEW.requested_by_actor_id IS DISTINCT FROM OLD.requested_by_actor_id
       OR NEW.target_level IS DISTINCT FROM OLD.target_level
       OR NEW.target_duration_minutes IS DISTINCT FROM OLD.target_duration_minutes
       OR NEW.intended_audience IS DISTINCT FROM OLD.intended_audience
       OR NEW.teaching_style IS DISTINCT FROM OLD.teaching_style
       OR NEW.locale IS DISTINCT FROM OLD.locale
       OR NEW.adapter IS DISTINCT FROM OLD.adapter
       OR NEW.provider IS DISTINCT FROM OLD.provider
       OR NEW.model IS DISTINCT FROM OLD.model
       OR NEW.normalized_schema_version IS DISTINCT FROM OLD.normalized_schema_version
       OR NEW.blueprint_schema_version IS DISTINCT FROM OLD.blueprint_schema_version
       OR NEW.draft_schema_version IS DISTINCT FROM OLD.draft_schema_version
       OR NEW.policy_version IS DISTINCT FROM OLD.policy_version
       OR NEW.prompt_template_sha256 IS DISTINCT FROM OLD.prompt_template_sha256
       OR NEW.input_manifest_sha256 IS DISTINCT FROM OLD.input_manifest_sha256
       OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'course generation scope is immutable' USING ERRCODE = '55000';
    END IF;
    IF OLD.status = 'queued' AND NEW.status NOT IN (
        'queued', 'planning', 'failed', 'rights_blocked'
    ) THEN
        RAISE EXCEPTION 'invalid generation transition' USING ERRCODE = '23514';
    ELSIF OLD.status = 'planning' AND NEW.status NOT IN (
        'planning', 'blueprint_review', 'retryable', 'failed', 'rights_blocked'
    ) THEN
        RAISE EXCEPTION 'invalid generation transition' USING ERRCODE = '23514';
    ELSIF OLD.status = 'blueprint_review' AND NEW.status NOT IN (
        'blueprint_review', 'generation_queued', 'rejected'
    ) THEN
        RAISE EXCEPTION 'invalid generation transition' USING ERRCODE = '23514';
    ELSIF OLD.status = 'generation_queued' AND NEW.status NOT IN (
        'generation_queued', 'generating', 'failed', 'rights_blocked'
    ) THEN
        RAISE EXCEPTION 'invalid generation transition' USING ERRCODE = '23514';
    ELSIF OLD.status = 'generating' AND NEW.status NOT IN (
        'generating', 'review_ready', 'retryable', 'failed', 'rights_blocked'
    ) THEN
        RAISE EXCEPTION 'invalid generation transition' USING ERRCODE = '23514';
    ELSIF OLD.status = 'review_ready' AND NEW.status NOT IN (
        'review_ready', 'canonicalized', 'rejected'
    ) THEN
        RAISE EXCEPTION 'invalid generation transition' USING ERRCODE = '23514';
    ELSIF OLD.status = 'retryable' AND NEW.status NOT IN (
        'retryable', 'planning', 'generating', 'failed', 'rights_blocked'
    ) THEN
        RAISE EXCEPTION 'invalid generation transition' USING ERRCODE = '23514';
    ELSIF OLD.status IN ('canonicalized', 'rejected', 'failed', 'rights_blocked')
       AND NEW.status <> OLD.status THEN
        RAISE EXCEPTION 'terminal generation run is immutable' USING ERRCODE = '23514';
    END IF;
    IF NEW.status IS DISTINCT FROM OLD.status AND NEW.row_version <> OLD.row_version + 1 THEN
        RAISE EXCEPTION 'generation transition requires next row version'
            USING ERRCODE = '23514';
    END IF;
    IF OLD.status = 'blueprint_review' AND NEW.status = 'generation_queued'
       AND NOT EXISTS (
            SELECT 1 FROM audit.course_generation_blueprint_decisions decision
             WHERE decision.tenant_id = NEW.tenant_id
               AND decision.generation_run_id = NEW.id
               AND decision.decision = 'approve'
               AND decision.reviewed_content_sha256 = OLD.blueprint_content_sha256
       ) THEN
        RAISE EXCEPTION 'exact blueprint approval is required' USING ERRCODE = '42501';
    END IF;
    IF OLD.status = 'blueprint_review' AND NEW.status = 'rejected'
       AND NOT EXISTS (
            SELECT 1 FROM audit.course_generation_blueprint_decisions decision
             WHERE decision.tenant_id = NEW.tenant_id
               AND decision.generation_run_id = NEW.id
               AND decision.decision = 'reject'
               AND decision.reviewed_content_sha256 = OLD.blueprint_content_sha256
       ) THEN
        RAISE EXCEPTION 'exact blueprint rejection is required' USING ERRCODE = '42501';
    END IF;
    IF OLD.status = 'review_ready' AND NEW.status = 'rejected'
       AND NOT EXISTS (
            SELECT 1 FROM audit.course_generation_rejections rejection
             WHERE rejection.tenant_id = NEW.tenant_id
               AND rejection.generation_run_id = NEW.id
               AND rejection.reviewed_output_sha256 = OLD.output_manifest_sha256
       ) THEN
        RAISE EXCEPTION 'exact generated revision rejection is required'
            USING ERRCODE = '42501';
    END IF;
    IF OLD.status = 'review_ready' AND NEW.status = 'canonicalized'
       AND NOT app.has_generation_canonicalization_evidence(
            NEW.tenant_id,
            NEW.id,
            OLD.output_manifest_sha256
       ) THEN
        RAISE EXCEPTION 'exact generated revision canonicalization is required'
            USING ERRCODE = '42501';
    END IF;
    IF OLD.status IN ('canonicalized', 'rejected', 'failed', 'rights_blocked')
       AND NEW IS DISTINCT FROM OLD THEN
        RAISE EXCEPTION 'terminal generation evidence is immutable' USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION app.enforce_generation_run_mutation() FROM PUBLIC;

CREATE OR REPLACE FUNCTION app.enforce_generation_attempt_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'course generation attempts are retained' USING ERRCODE = '55000';
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id
       OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
       OR NEW.generation_run_id IS DISTINCT FROM OLD.generation_run_id
       OR NEW.attempt_number IS DISTINCT FROM OLD.attempt_number
       OR NEW.stage IS DISTINCT FROM OLD.stage
       OR NEW.input_manifest_sha256 IS DISTINCT FROM OLD.input_manifest_sha256
       OR NEW.started_at IS DISTINCT FROM OLD.started_at THEN
        RAISE EXCEPTION 'course generation attempt identity is immutable'
            USING ERRCODE = '55000';
    END IF;
    IF OLD.outcome <> 'running' AND NEW IS DISTINCT FROM OLD THEN
        RAISE EXCEPTION 'completed course generation attempt is immutable'
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION app.enforce_generation_attempt_mutation() FROM PUBLIC;

CREATE OR REPLACE FUNCTION app.enforce_generation_blueprint_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'course generation blueprints are retained' USING ERRCODE = '55000';
    END IF;
    IF OLD.status = 'reviewable'
       AND NEW.status IN ('approved', 'rejected')
       AND NEW.id = OLD.id
       AND NEW.tenant_id = OLD.tenant_id
       AND NEW.generation_run_id = OLD.generation_run_id
       AND NEW.revision = OLD.revision
       AND NEW.schema_version = OLD.schema_version
       AND NEW.title = OLD.title
       AND NEW.description = OLD.description
       AND NEW.intended_audience = OLD.intended_audience
       AND NEW.prerequisites = OLD.prerequisites
       AND NEW.learning_outcomes = OLD.learning_outcomes
       AND NEW.projection = OLD.projection
       AND NEW.content_sha256 = OLD.content_sha256
       AND NEW.created_at = OLD.created_at THEN
        RETURN NEW;
    END IF;
    IF NEW IS DISTINCT FROM OLD THEN
        RAISE EXCEPTION 'generation blueprint projection is immutable'
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION app.enforce_generation_blueprint_mutation() FROM PUBLIC;

CREATE OR REPLACE FUNCTION app.reject_generation_evidence_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    RAISE EXCEPTION 'generation evidence is immutable' USING ERRCODE = '55000';
END
$$;
REVOKE ALL ON FUNCTION app.reject_generation_evidence_mutation() FROM PUBLIC;

CREATE TRIGGER trg_generation_runs_guard
BEFORE INSERT OR UPDATE OR DELETE ON integration.course_generation_runs
FOR EACH ROW EXECUTE FUNCTION app.enforce_generation_run_mutation();
CREATE TRIGGER trg_generation_attempts_guard
BEFORE UPDATE OR DELETE ON integration.course_generation_attempts
FOR EACH ROW EXECUTE FUNCTION app.enforce_generation_attempt_mutation();
CREATE TRIGGER trg_generation_blueprints_guard
BEFORE UPDATE OR DELETE ON app.course_generation_blueprints
FOR EACH ROW EXECUTE FUNCTION app.enforce_generation_blueprint_mutation();
CREATE TRIGGER trg_generation_snapshots_immutable
BEFORE UPDATE OR DELETE ON integration.course_generation_snapshots
FOR EACH ROW EXECUTE FUNCTION app.reject_generation_evidence_mutation();
CREATE TRIGGER trg_generation_items_immutable
BEFORE UPDATE OR DELETE ON app.course_generation_blueprint_items
FOR EACH ROW EXECUTE FUNCTION app.reject_generation_evidence_mutation();
CREATE TRIGGER trg_generated_lessons_immutable
BEFORE UPDATE OR DELETE ON app.generated_lesson_artifacts
FOR EACH ROW EXECUTE FUNCTION app.reject_generation_evidence_mutation();
CREATE TRIGGER trg_generation_edges_immutable
BEFORE UPDATE OR DELETE ON app.course_generation_source_edges
FOR EACH ROW EXECUTE FUNCTION app.reject_generation_evidence_mutation();
CREATE TRIGGER trg_generation_decisions_immutable
BEFORE UPDATE OR DELETE ON audit.course_generation_blueprint_decisions
FOR EACH ROW EXECUTE FUNCTION app.reject_generation_evidence_mutation();
CREATE TRIGGER trg_generation_rejections_immutable
BEFORE UPDATE OR DELETE ON audit.course_generation_rejections
FOR EACH ROW EXECUTE FUNCTION app.reject_generation_evidence_mutation();

ALTER TABLE integration.course_generation_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE integration.course_generation_runs FORCE ROW LEVEL SECURITY;
CREATE POLICY generation_runs_api_select ON integration.course_generation_runs
    FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'course_generation.runs.read'));
CREATE POLICY generation_runs_api_insert ON integration.course_generation_runs
    FOR INSERT TO lms_api_runtime
    WITH CHECK (app.has_permission(tenant_id, 'course_generation.runs.create'));
CREATE POLICY generation_runs_api_review ON integration.course_generation_runs
    FOR UPDATE TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'course_generation.blueprints.review'))
    WITH CHECK (app.has_permission(tenant_id, 'course_generation.blueprints.review'));
CREATE POLICY generation_runs_worker_select ON integration.course_generation_runs
    FOR SELECT TO lms_worker_runtime
    USING (app.has_generation_event_scope(tenant_id, id));
CREATE POLICY generation_runs_worker_update ON integration.course_generation_runs
    FOR UPDATE TO lms_worker_runtime
    USING (app.has_generation_event_scope(tenant_id, id))
    WITH CHECK (app.has_generation_event_scope(tenant_id, id));

ALTER TABLE integration.course_generation_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE integration.course_generation_attempts FORCE ROW LEVEL SECURITY;
CREATE POLICY generation_attempts_api_select ON integration.course_generation_attempts
    FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'course_generation.runs.read'));
CREATE POLICY generation_attempts_worker_select ON integration.course_generation_attempts
    FOR SELECT TO lms_worker_runtime
    USING (app.has_generation_event_scope(tenant_id, generation_run_id));
CREATE POLICY generation_attempts_worker_insert ON integration.course_generation_attempts
    FOR INSERT TO lms_worker_runtime
    WITH CHECK (app.has_generation_event_scope(tenant_id, generation_run_id));
CREATE POLICY generation_attempts_worker_update ON integration.course_generation_attempts
    FOR UPDATE TO lms_worker_runtime
    USING (app.has_generation_event_scope(tenant_id, generation_run_id))
    WITH CHECK (app.has_generation_event_scope(tenant_id, generation_run_id));

ALTER TABLE integration.course_generation_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE integration.course_generation_snapshots FORCE ROW LEVEL SECURITY;
CREATE POLICY generation_snapshots_api_select ON integration.course_generation_snapshots
    FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'course_generation.runs.read'));
CREATE POLICY generation_snapshots_api_insert ON integration.course_generation_snapshots
    FOR INSERT TO lms_api_runtime
    WITH CHECK (app.has_permission(tenant_id, 'course_generation.runs.create'));

ALTER TABLE app.course_generation_blueprints ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.course_generation_blueprints FORCE ROW LEVEL SECURITY;
CREATE POLICY generation_blueprints_api_select ON app.course_generation_blueprints
    FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'course_generation.runs.read'));
CREATE POLICY generation_blueprints_api_review ON app.course_generation_blueprints
    FOR UPDATE TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'course_generation.blueprints.review'))
    WITH CHECK (app.has_permission(tenant_id, 'course_generation.blueprints.review'));
CREATE POLICY generation_blueprints_worker_select ON app.course_generation_blueprints
    FOR SELECT TO lms_worker_runtime
    USING (app.has_generation_event_scope(tenant_id, generation_run_id));
CREATE POLICY generation_blueprints_worker_insert ON app.course_generation_blueprints
    FOR INSERT TO lms_worker_runtime
    WITH CHECK (app.has_generation_event_scope(tenant_id, generation_run_id));

ALTER TABLE app.course_generation_blueprint_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.course_generation_blueprint_items FORCE ROW LEVEL SECURITY;
CREATE POLICY generation_items_api_select ON app.course_generation_blueprint_items
    FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'course_generation.runs.read'));
CREATE POLICY generation_items_worker_select ON app.course_generation_blueprint_items
    FOR SELECT TO lms_worker_runtime
    USING (app.has_generation_event_scope(tenant_id, generation_run_id));
CREATE POLICY generation_items_worker_insert ON app.course_generation_blueprint_items
    FOR INSERT TO lms_worker_runtime
    WITH CHECK (app.has_generation_event_scope(tenant_id, generation_run_id));

ALTER TABLE app.generated_lesson_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.generated_lesson_artifacts FORCE ROW LEVEL SECURITY;
CREATE POLICY generated_lessons_api_select ON app.generated_lesson_artifacts
    FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'course_generation.runs.read'));
CREATE POLICY generated_lessons_worker_select ON app.generated_lesson_artifacts
    FOR SELECT TO lms_worker_runtime
    USING (app.has_generation_event_scope(tenant_id, generation_run_id));
CREATE POLICY generated_lessons_worker_insert ON app.generated_lesson_artifacts
    FOR INSERT TO lms_worker_runtime
    WITH CHECK (app.has_generation_event_scope(tenant_id, generation_run_id));

ALTER TABLE app.course_generation_source_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.course_generation_source_edges FORCE ROW LEVEL SECURITY;
CREATE POLICY generation_edges_api_select ON app.course_generation_source_edges
    FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'course_generation.runs.read'));
CREATE POLICY generation_edges_worker_select ON app.course_generation_source_edges
    FOR SELECT TO lms_worker_runtime
    USING (app.has_generation_event_scope(tenant_id, generation_run_id));
CREATE POLICY generation_edges_worker_insert ON app.course_generation_source_edges
    FOR INSERT TO lms_worker_runtime
    WITH CHECK (app.has_generation_event_scope(tenant_id, generation_run_id));

ALTER TABLE audit.course_generation_blueprint_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit.course_generation_blueprint_decisions FORCE ROW LEVEL SECURITY;
CREATE POLICY generation_decisions_api_select ON audit.course_generation_blueprint_decisions
    FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'course_generation.runs.read'));
CREATE POLICY generation_decisions_api_insert ON audit.course_generation_blueprint_decisions
    FOR INSERT TO lms_api_runtime
    WITH CHECK (
        decided_by_actor_id = app.current_actor_id()
        AND app.has_permission(tenant_id, 'course_generation.blueprints.review')
    );

ALTER TABLE audit.course_generation_rejections ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit.course_generation_rejections FORCE ROW LEVEL SECURITY;
CREATE POLICY generation_rejections_api_select ON audit.course_generation_rejections
    FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'course_generation.runs.read'));
CREATE POLICY generation_rejections_api_insert ON audit.course_generation_rejections
    FOR INSERT TO lms_api_runtime
    WITH CHECK (
        rejected_by_actor_id = app.current_actor_id()
        AND app.has_permission(tenant_id, 'course_generation.blueprints.review')
    );

CREATE POLICY source_documents_generation_worker ON app.source_documents
    FOR SELECT TO lms_worker_runtime
    USING (
        EXISTS (
            SELECT 1 FROM integration.course_generation_runs run
             WHERE run.id = app.current_job_id()
               AND run.tenant_id = source_documents.tenant_id
               AND run.source_document_id = source_documents.id
               AND app.current_job_stage() LIKE 'generation\_%' ESCAPE '\'
        )
    );
CREATE POLICY source_versions_generation_worker ON app.source_document_versions
    FOR SELECT TO lms_worker_runtime
    USING (app.has_generation_source_scope(tenant_id, id));
CREATE POLICY source_auth_generation_worker ON app.source_use_authorizations
    FOR SELECT TO lms_worker_runtime
    USING (app.has_generation_source_scope(tenant_id, source_version_id));
CREATE POLICY ingestion_runs_generation_worker ON integration.document_ingestion_runs
    FOR SELECT TO lms_worker_runtime
    USING (
        EXISTS (
            SELECT 1 FROM integration.course_generation_runs run
             WHERE run.id = app.current_job_id()
               AND run.tenant_id = document_ingestion_runs.tenant_id
               AND run.ingestion_run_id = document_ingestion_runs.id
               AND app.current_job_stage() LIKE 'generation\_%' ESCAPE '\'
        )
    );
CREATE POLICY document_sections_generation_worker ON app.document_sections
    FOR SELECT TO lms_worker_runtime
    USING (app.has_generation_source_scope(tenant_id, source_version_id));
CREATE POLICY document_elements_generation_worker ON app.document_elements
    FOR SELECT TO lms_worker_runtime
    USING (app.has_generation_source_scope(tenant_id, source_version_id));
CREATE POLICY section_elements_generation_worker ON app.document_section_elements
    FOR SELECT TO lms_worker_runtime
    USING (app.has_generation_source_scope(tenant_id, source_version_id));

CREATE POLICY idempotency_generation_api ON integration.idempotency_reservations
    FOR ALL TO lms_api_runtime
    USING (
        actor_id = app.current_actor_id()
        AND app.has_permission(tenant_id, 'course_generation.runs.create')
    )
    WITH CHECK (
        actor_id = app.current_actor_id()
        AND app.has_permission(tenant_id, 'course_generation.runs.create')
    );
CREATE POLICY audit_generation_api_insert ON audit.tenant_audit_facts
    FOR INSERT TO lms_api_runtime
    WITH CHECK (
        tenant_id = app.current_tenant_id()
        AND (
            app.has_permission(tenant_id, 'course_generation.runs.create')
            OR app.has_permission(tenant_id, 'course_generation.blueprints.review')
        )
    );
CREATE POLICY outbox_generation_api_insert ON integration.tenant_outbox_facts
    FOR INSERT TO lms_api_runtime
    WITH CHECK (
        tenant_id = app.current_tenant_id()
        AND (
            app.has_permission(tenant_id, 'course_generation.runs.create')
            OR app.has_permission(tenant_id, 'course_generation.blueprints.review')
        )
    );
CREATE POLICY audit_generation_worker_insert ON audit.tenant_audit_facts
    FOR INSERT TO lms_worker_runtime
    WITH CHECK (app.has_generation_event_scope(tenant_id, subject_id));
CREATE POLICY outbox_generation_worker_insert ON integration.tenant_outbox_facts
    FOR INSERT TO lms_worker_runtime
    WITH CHECK (app.has_generation_event_scope(tenant_id, aggregate_id));

GRANT SELECT, INSERT, UPDATE ON integration.course_generation_runs TO lms_api_runtime;
GRANT SELECT ON integration.course_generation_attempts,
    integration.course_generation_snapshots,
    app.course_generation_blueprint_items,
    app.generated_lesson_artifacts,
    app.course_generation_source_edges,
    audit.course_generation_blueprint_decisions,
    audit.course_generation_rejections TO lms_api_runtime;
GRANT SELECT, INSERT ON integration.course_generation_snapshots TO lms_api_runtime;
GRANT SELECT, UPDATE ON app.course_generation_blueprints TO lms_api_runtime;
GRANT INSERT ON audit.course_generation_blueprint_decisions,
    audit.course_generation_rejections TO lms_api_runtime;

GRANT SELECT, UPDATE ON integration.course_generation_runs TO lms_worker_runtime;
GRANT SELECT, INSERT, UPDATE ON integration.course_generation_attempts
    TO lms_worker_runtime;
GRANT SELECT, INSERT ON app.course_generation_blueprints,
    app.course_generation_blueprint_items,
    app.generated_lesson_artifacts,
    app.course_generation_source_edges TO lms_worker_runtime;
"""


REVERSE_SQL = r"""
REVOKE ALL ON integration.course_generation_runs,
    integration.course_generation_attempts,
    integration.course_generation_snapshots,
    app.course_generation_blueprints,
    app.course_generation_blueprint_items,
    app.generated_lesson_artifacts,
    app.course_generation_source_edges,
    audit.course_generation_blueprint_decisions,
    audit.course_generation_rejections FROM lms_api_runtime, lms_worker_runtime;

DROP POLICY IF EXISTS outbox_generation_worker_insert ON integration.tenant_outbox_facts;
DROP POLICY IF EXISTS audit_generation_worker_insert ON audit.tenant_audit_facts;
DROP POLICY IF EXISTS outbox_generation_api_insert ON integration.tenant_outbox_facts;
DROP POLICY IF EXISTS audit_generation_api_insert ON audit.tenant_audit_facts;
DROP POLICY IF EXISTS idempotency_generation_api ON integration.idempotency_reservations;
DROP POLICY IF EXISTS section_elements_generation_worker ON app.document_section_elements;
DROP POLICY IF EXISTS document_elements_generation_worker ON app.document_elements;
DROP POLICY IF EXISTS document_sections_generation_worker ON app.document_sections;
DROP POLICY IF EXISTS ingestion_runs_generation_worker ON integration.document_ingestion_runs;
DROP POLICY IF EXISTS source_auth_generation_worker ON app.source_use_authorizations;
DROP POLICY IF EXISTS source_versions_generation_worker ON app.source_document_versions;
DROP POLICY IF EXISTS source_documents_generation_worker ON app.source_documents;
DROP POLICY IF EXISTS generation_rejections_api_insert ON audit.course_generation_rejections;
DROP POLICY IF EXISTS generation_rejections_api_select ON audit.course_generation_rejections;
DROP POLICY IF EXISTS generation_decisions_api_insert
    ON audit.course_generation_blueprint_decisions;
DROP POLICY IF EXISTS generation_decisions_api_select
    ON audit.course_generation_blueprint_decisions;
DROP POLICY IF EXISTS generation_edges_worker_insert ON app.course_generation_source_edges;
DROP POLICY IF EXISTS generation_edges_worker_select ON app.course_generation_source_edges;
DROP POLICY IF EXISTS generation_edges_api_select ON app.course_generation_source_edges;
DROP POLICY IF EXISTS generated_lessons_worker_insert ON app.generated_lesson_artifacts;
DROP POLICY IF EXISTS generated_lessons_worker_select ON app.generated_lesson_artifacts;
DROP POLICY IF EXISTS generated_lessons_api_select ON app.generated_lesson_artifacts;
DROP POLICY IF EXISTS generation_items_worker_insert
    ON app.course_generation_blueprint_items;
DROP POLICY IF EXISTS generation_items_worker_select
    ON app.course_generation_blueprint_items;
DROP POLICY IF EXISTS generation_items_api_select ON app.course_generation_blueprint_items;
DROP POLICY IF EXISTS generation_blueprints_worker_insert
    ON app.course_generation_blueprints;
DROP POLICY IF EXISTS generation_blueprints_worker_select
    ON app.course_generation_blueprints;
DROP POLICY IF EXISTS generation_blueprints_api_review ON app.course_generation_blueprints;
DROP POLICY IF EXISTS generation_blueprints_api_select ON app.course_generation_blueprints;
DROP POLICY IF EXISTS generation_snapshots_api_insert
    ON integration.course_generation_snapshots;
DROP POLICY IF EXISTS generation_snapshots_api_select
    ON integration.course_generation_snapshots;
DROP POLICY IF EXISTS generation_attempts_worker_update
    ON integration.course_generation_attempts;
DROP POLICY IF EXISTS generation_attempts_worker_insert
    ON integration.course_generation_attempts;
DROP POLICY IF EXISTS generation_attempts_worker_select
    ON integration.course_generation_attempts;
DROP POLICY IF EXISTS generation_attempts_api_select
    ON integration.course_generation_attempts;
DROP POLICY IF EXISTS generation_runs_worker_update ON integration.course_generation_runs;
DROP POLICY IF EXISTS generation_runs_worker_select ON integration.course_generation_runs;
DROP POLICY IF EXISTS generation_runs_api_review ON integration.course_generation_runs;
DROP POLICY IF EXISTS generation_runs_api_insert ON integration.course_generation_runs;
DROP POLICY IF EXISTS generation_runs_api_select ON integration.course_generation_runs;

DROP TRIGGER IF EXISTS trg_generation_rejections_immutable
    ON audit.course_generation_rejections;
DROP TRIGGER IF EXISTS trg_generation_decisions_immutable
    ON audit.course_generation_blueprint_decisions;
DROP TRIGGER IF EXISTS trg_generation_edges_immutable ON app.course_generation_source_edges;
DROP TRIGGER IF EXISTS trg_generated_lessons_immutable ON app.generated_lesson_artifacts;
DROP TRIGGER IF EXISTS trg_generation_items_immutable
    ON app.course_generation_blueprint_items;
DROP TRIGGER IF EXISTS trg_generation_snapshots_immutable
    ON integration.course_generation_snapshots;
DROP TRIGGER IF EXISTS trg_generation_blueprints_guard ON app.course_generation_blueprints;
DROP TRIGGER IF EXISTS trg_generation_attempts_guard
    ON integration.course_generation_attempts;
DROP TRIGGER IF EXISTS trg_generation_runs_guard ON integration.course_generation_runs;
DROP FUNCTION IF EXISTS app.reject_generation_evidence_mutation();
DROP FUNCTION IF EXISTS app.enforce_generation_blueprint_mutation();
DROP FUNCTION IF EXISTS app.enforce_generation_attempt_mutation();
DROP FUNCTION IF EXISTS app.enforce_generation_run_mutation();
DROP FUNCTION IF EXISTS app.has_generation_canonicalization_evidence(uuid, uuid, text);
DROP FUNCTION IF EXISTS app.has_generation_source_scope(uuid, uuid);
DROP FUNCTION IF EXISTS app.has_generation_event_scope(uuid, uuid);

ALTER TABLE app.generated_lesson_artifacts
    DROP CONSTRAINT IF EXISTS ck_generated_lesson_document_object,
    DROP CONSTRAINT IF EXISTS fk_generated_lessons_same_tenant_section,
    DROP CONSTRAINT IF EXISTS fk_generated_lessons_same_tenant_version,
    DROP CONSTRAINT IF EXISTS fk_generated_lessons_same_tenant_item,
    DROP CONSTRAINT IF EXISTS fk_generated_lessons_same_tenant_run;
ALTER TABLE app.course_generation_source_edges
    DROP CONSTRAINT IF EXISTS fk_generation_edges_same_tenant_artifact,
    DROP CONSTRAINT IF EXISTS fk_generation_edges_same_tenant_item,
    DROP CONSTRAINT IF EXISTS fk_generation_edges_same_tenant_section,
    DROP CONSTRAINT IF EXISTS fk_generation_edges_same_tenant_version,
    DROP CONSTRAINT IF EXISTS fk_generation_edges_same_tenant_run;
ALTER TABLE app.course_generation_blueprint_items
    DROP CONSTRAINT IF EXISTS fk_generation_items_same_tenant_section,
    DROP CONSTRAINT IF EXISTS fk_generation_items_same_tenant_version,
    DROP CONSTRAINT IF EXISTS fk_generation_items_same_tenant_parent,
    DROP CONSTRAINT IF EXISTS fk_generation_items_same_tenant_blueprint,
    DROP CONSTRAINT IF EXISTS fk_generation_items_same_tenant_run;
ALTER TABLE app.course_generation_blueprints
    DROP CONSTRAINT IF EXISTS ck_generation_blueprint_outcomes_array,
    DROP CONSTRAINT IF EXISTS ck_generation_blueprint_prerequisites_array,
    DROP CONSTRAINT IF EXISTS ck_generation_blueprint_projection_object,
    DROP CONSTRAINT IF EXISTS fk_generation_blueprints_same_tenant_run;
ALTER TABLE integration.course_generation_snapshots
    DROP CONSTRAINT IF EXISTS ck_generation_snapshot_metadata_object,
    DROP CONSTRAINT IF EXISTS fk_generation_snapshots_same_tenant_run;
ALTER TABLE integration.course_generation_attempts
    DROP CONSTRAINT IF EXISTS ck_generation_attempts_observation_object,
    DROP CONSTRAINT IF EXISTS ck_generation_attempts_completion_shape,
    DROP CONSTRAINT IF EXISTS ck_generation_attempts_stage,
    DROP CONSTRAINT IF EXISTS fk_generation_attempts_same_tenant_run;
ALTER TABLE audit.course_generation_blueprint_decisions
    DROP CONSTRAINT IF EXISTS fk_generation_decisions_same_tenant_blueprint,
    DROP CONSTRAINT IF EXISTS fk_generation_decisions_same_tenant_run;
ALTER TABLE audit.course_generation_rejections
    DROP CONSTRAINT IF EXISTS fk_generation_rejections_same_tenant_run;
ALTER TABLE integration.course_generation_runs
    DROP CONSTRAINT IF EXISTS ck_generation_runs_result_shape,
    DROP CONSTRAINT IF EXISTS ck_generation_runs_lease_shape,
    DROP CONSTRAINT IF EXISTS fk_generation_runs_same_tenant_superseded,
    DROP CONSTRAINT IF EXISTS fk_generation_runs_same_tenant_authorization,
    DROP CONSTRAINT IF EXISTS fk_generation_runs_same_tenant_ingestion,
    DROP CONSTRAINT IF EXISTS fk_generation_runs_same_tenant_version,
    DROP CONSTRAINT IF EXISTS fk_generation_runs_same_tenant_document;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("course_generation", "0003_generation_rejections"),
        ("documents", "0005_ingestion_security"),
        ("tenancy", "0002_secure_invitation_bootstrap"),
    ]

    operations = [
        migrations.RunPython(seed_generation_permissions, unseed_generation_permissions),
        migrations.RunSQL(FORWARD_SQL, REVERSE_SQL),
    ]
