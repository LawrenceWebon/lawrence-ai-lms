from __future__ import annotations

from django.db import migrations

FORWARD_SQL = r"""
ALTER TABLE audit.course_generation_canonicalizations OWNER TO lms_object_owner;
ALTER TABLE app.course_generation_canonicalization_edges OWNER TO lms_object_owner;

REVOKE ALL ON audit.course_generation_canonicalizations,
    app.course_generation_canonicalization_edges FROM PUBLIC;

ALTER TABLE audit.course_generation_canonicalizations
    ADD CONSTRAINT fk_generation_canonical_same_tenant_run
    FOREIGN KEY (tenant_id, generation_run_id)
    REFERENCES integration.course_generation_runs (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_generation_canonical_same_tenant_course
    FOREIGN KEY (tenant_id, course_id)
    REFERENCES app.courses (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_generation_canonical_same_tenant_version
    FOREIGN KEY (tenant_id, course_id, course_version_id)
    REFERENCES app.course_versions (tenant_id, course_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT ck_generation_canonical_slug
    CHECK (requested_course_slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$');

ALTER TABLE app.course_generation_canonicalization_edges
    ADD CONSTRAINT fk_canonical_edges_same_tenant_canonical
    FOREIGN KEY (tenant_id, canonicalization_id)
    REFERENCES audit.course_generation_canonicalizations (tenant_id, id)
    ON DELETE RESTRICT,
    ADD CONSTRAINT fk_canonical_edges_same_tenant_run
    FOREIGN KEY (tenant_id, generation_run_id)
    REFERENCES integration.course_generation_runs (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_canonical_edges_same_tenant_artifact
    FOREIGN KEY (tenant_id, generation_run_id, generated_artifact_id)
    REFERENCES app.generated_lesson_artifacts (tenant_id, generation_run_id, id)
    ON DELETE RESTRICT,
    ADD CONSTRAINT fk_canonical_edges_same_tenant_version_source
    FOREIGN KEY (tenant_id, source_version_id)
    REFERENCES app.source_document_versions (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_canonical_edges_same_tenant_section_source
    FOREIGN KEY (tenant_id, source_version_id, source_section_id)
    REFERENCES app.document_sections (tenant_id, source_version_id, id)
    ON DELETE RESTRICT,
    ADD CONSTRAINT fk_canonical_edges_same_tenant_course
    FOREIGN KEY (tenant_id, course_id)
    REFERENCES app.courses (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_canonical_edges_same_tenant_version
    FOREIGN KEY (tenant_id, course_id, course_version_id)
    REFERENCES app.course_versions (tenant_id, course_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT ck_canonical_edges_target_ids
    CHECK (curriculum_section_id IS NOT NULL AND lesson_id IS NOT NULL
           AND content_block_id IS NOT NULL);

CREATE FUNCTION app.validate_canonicalization_target_snapshot()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
SET row_security = off
AS $$
BEGIN
    PERFORM 1
      FROM app.curriculum_sections section
      JOIN app.lessons lesson
        ON lesson.tenant_id = section.tenant_id
       AND lesson.course_version_id = section.course_version_id
       AND lesson.section_id = section.id
      JOIN app.lesson_content_blocks block
        ON block.tenant_id = lesson.tenant_id
       AND block.course_version_id = lesson.course_version_id
       AND block.lesson_id = lesson.id
      JOIN app.generated_lesson_artifacts artifact
        ON artifact.tenant_id = block.tenant_id
       AND artifact.id = NEW.generated_artifact_id
       AND artifact.generation_run_id = NEW.generation_run_id
       AND artifact.source_version_id = NEW.source_version_id
       AND artifact.source_section_id = NEW.source_section_id
       AND artifact.document = block.document
      JOIN audit.course_generation_canonicalizations canonicalization
        ON canonicalization.tenant_id = NEW.tenant_id
       AND canonicalization.id = NEW.canonicalization_id
       AND canonicalization.generation_run_id = NEW.generation_run_id
       AND canonicalization.course_id = NEW.course_id
       AND canonicalization.course_version_id = NEW.course_version_id
     WHERE section.tenant_id = NEW.tenant_id
       AND section.course_version_id = NEW.course_version_id
       AND section.id = NEW.curriculum_section_id
       AND lesson.id = NEW.lesson_id
       AND block.id = NEW.content_block_id
     FOR SHARE OF section, lesson, block, artifact;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'canonicalization target scope mismatch' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION app.validate_canonicalization_target_snapshot() FROM PUBLIC;
CREATE TRIGGER trg_canonicalization_target_snapshot
BEFORE INSERT ON app.course_generation_canonicalization_edges
FOR EACH ROW EXECUTE FUNCTION app.validate_canonicalization_target_snapshot();

CREATE FUNCTION app.lock_generated_course_publication(
    p_tenant_id uuid, p_course_id uuid, p_version_id uuid
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
SET row_security = off
AS $$
DECLARE
    version_row app.course_versions%ROWTYPE;
    generation integration.course_generation_runs%ROWTYPE;
    authorization_row app.source_use_authorizations%ROWTYPE;
BEGIN
    IF app.current_tenant_id() IS DISTINCT FROM p_tenant_id
       OR app.current_actor_id() IS NULL
       OR NOT (app.has_permission(p_tenant_id, 'courses.review')
               OR app.has_permission(p_tenant_id, 'courses.publish')) THEN
        RETURN false;
    END IF;
    SELECT * INTO version_row FROM app.course_versions
     WHERE tenant_id = p_tenant_id AND course_id = p_course_id AND id = p_version_id
     FOR NO KEY UPDATE;
    IF NOT FOUND THEN RETURN false; END IF;

    SELECT run.* INTO generation
      FROM integration.course_generation_runs run
      JOIN audit.course_generation_canonicalizations canonicalization
        ON canonicalization.tenant_id = run.tenant_id
       AND canonicalization.generation_run_id = run.id
     WHERE canonicalization.tenant_id = p_tenant_id
       AND canonicalization.course_id = p_course_id
       AND canonicalization.course_version_id IN (
           WITH RECURSIVE ancestors AS (
               SELECT id, predecessor_version_id FROM app.course_versions
                WHERE tenant_id = p_tenant_id AND course_id = p_course_id AND id = p_version_id
               UNION
               SELECT parent.id, parent.predecessor_version_id
                 FROM app.course_versions parent JOIN ancestors child
                   ON parent.id = child.predecessor_version_id
                WHERE parent.tenant_id = p_tenant_id AND parent.course_id = p_course_id
           ) SELECT id FROM ancestors
       )
       AND run.status = 'canonicalized'
       AND canonicalization.reviewed_output_sha256 = run.output_manifest_sha256;
    IF NOT FOUND THEN
        RETURN version_row.origin_type = 'manual'
           AND NOT EXISTS (
               SELECT 1 FROM audit.course_generation_canonicalizations
                WHERE tenant_id = p_tenant_id AND course_id = p_course_id
           );
    END IF;

    PERFORM 1 FROM app.source_documents document
     WHERE document.tenant_id = p_tenant_id AND document.id = generation.source_document_id
       AND document.current_version_id = generation.source_version_id
     FOR NO KEY UPDATE;
    IF NOT FOUND THEN RETURN false; END IF;
    PERFORM 1 FROM app.source_document_versions source
     WHERE source.tenant_id = p_tenant_id AND source.id = generation.source_version_id
       AND source.source_document_id = generation.source_document_id
       AND source.admission_status = 'admitted'
     FOR NO KEY UPDATE;
    IF NOT FOUND THEN RETURN false; END IF;

    SELECT * INTO authorization_row FROM app.source_use_authorizations
     WHERE tenant_id = p_tenant_id AND id = generation.generate_authorization_id
       AND source_document_id = generation.source_document_id
       AND source_version_id = generation.source_version_id AND operation = 'generate'
     FOR NO KEY UPDATE;
    RETURN FOUND AND authorization_row.status = 'active'
       AND authorization_row.valid_from IS NOT NULL
       AND authorization_row.valid_from <= statement_timestamp()
       AND (authorization_row.valid_until IS NULL
            OR authorization_row.valid_until > statement_timestamp());
END
$$;
REVOKE ALL ON FUNCTION app.lock_generated_course_publication(uuid, uuid, uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app.lock_generated_course_publication(uuid, uuid, uuid)
    TO lms_api_runtime;

CREATE FUNCTION app.guard_generated_course_publication()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
SET row_security = off
AS $$
BEGIN
    IF NEW.status IN ('approved', 'published') AND NEW.status IS DISTINCT FROM OLD.status
       AND (NEW.origin_type = 'ai_assisted' OR EXISTS (
           SELECT 1 FROM audit.course_generation_canonicalizations
            WHERE tenant_id = NEW.tenant_id AND course_id = NEW.course_id
       ))
       AND NOT app.lock_generated_course_publication(NEW.tenant_id, NEW.course_id, NEW.id) THEN
        RAISE EXCEPTION 'generated course source rights unavailable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION app.guard_generated_course_publication() FROM PUBLIC;
CREATE TRIGGER trg_generated_course_publication_rights
BEFORE UPDATE ON app.course_versions
FOR EACH ROW EXECUTE FUNCTION app.guard_generated_course_publication();

CREATE OR REPLACE FUNCTION app.has_generation_canonicalization_evidence(
    p_tenant_id uuid,
    p_generation_run_id uuid,
    p_output_manifest_sha256 text
)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog
SET row_security = off
AS $$
    SELECT EXISTS (
        SELECT 1
          FROM audit.course_generation_canonicalizations canonicalization
         WHERE canonicalization.tenant_id = p_tenant_id
           AND canonicalization.generation_run_id = p_generation_run_id
           AND canonicalization.reviewed_output_sha256 = p_output_manifest_sha256
    )
$$;
REVOKE ALL ON FUNCTION app.has_generation_canonicalization_evidence(uuid, uuid, text)
    FROM PUBLIC;

CREATE OR REPLACE FUNCTION app.lock_generation_canonicalization_scope(
    p_tenant_id uuid,
    p_generation_run_id uuid,
    p_expected_row_version bigint,
    p_expected_output_manifest_sha256 text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
SET row_security = off
AS $$
DECLARE
    generation integration.course_generation_runs%ROWTYPE;
    authorization_row app.source_use_authorizations%ROWTYPE;
BEGIN
    IF app.current_actor_id() IS NULL
       OR app.current_tenant_id() IS DISTINCT FROM p_tenant_id
       OR NOT app.has_permission(
            p_tenant_id,
            'course_generation.drafts.canonicalize'
       )
       OR NOT app.has_permission(p_tenant_id, 'courses.drafts.write') THEN
        RETURN false;
    END IF;

    SELECT run.* INTO generation
      FROM integration.course_generation_runs run
     WHERE run.tenant_id = p_tenant_id
       AND run.id = p_generation_run_id
       AND run.status = 'review_ready'
       AND run.row_version = p_expected_row_version
       AND run.output_manifest_sha256 = p_expected_output_manifest_sha256
     FOR UPDATE;
    IF NOT FOUND THEN
        RETURN false;
    END IF;

    PERFORM 1
      FROM app.source_documents document
     WHERE document.tenant_id = generation.tenant_id
       AND document.id = generation.source_document_id
       AND document.current_version_id = generation.source_version_id
     FOR NO KEY UPDATE;
    IF NOT FOUND THEN
        RETURN false;
    END IF;

    PERFORM 1
      FROM app.source_document_versions version
     WHERE version.tenant_id = generation.tenant_id
       AND version.source_document_id = generation.source_document_id
       AND version.id = generation.source_version_id
       AND version.admission_status = 'admitted'
     FOR NO KEY UPDATE;
    IF NOT FOUND THEN
        RETURN false;
    END IF;

    PERFORM 1
      FROM integration.document_ingestion_runs ingestion
     WHERE ingestion.tenant_id = generation.tenant_id
       AND ingestion.source_document_id = generation.source_document_id
       AND ingestion.source_version_id = generation.source_version_id
       AND ingestion.id = generation.ingestion_run_id
       AND ingestion.status = 'ready_for_generation'
     FOR NO KEY UPDATE;
    IF NOT FOUND THEN
        RETURN false;
    END IF;

    SELECT auth.* INTO authorization_row
      FROM app.source_use_authorizations auth
     WHERE auth.tenant_id = generation.tenant_id
       AND auth.source_document_id = generation.source_document_id
       AND auth.source_version_id = generation.source_version_id
       AND auth.id = generation.generate_authorization_id
       AND auth.operation = 'generate'
     FOR NO KEY UPDATE;
    IF NOT FOUND
       OR authorization_row.status <> 'active'
       OR authorization_row.valid_from IS NULL
       OR authorization_row.valid_from > statement_timestamp()
       OR (
            authorization_row.valid_until IS NOT NULL
            AND authorization_row.valid_until <= statement_timestamp()
       ) THEN
        RETURN false;
    END IF;

    PERFORM 1
      FROM app.course_generation_blueprints blueprint
     WHERE blueprint.tenant_id = generation.tenant_id
       AND blueprint.generation_run_id = generation.id
       AND blueprint.status = 'approved'
     FOR SHARE;
    IF NOT FOUND THEN
        RETURN false;
    END IF;

    PERFORM 1
      FROM app.generated_lesson_artifacts artifact
     WHERE artifact.tenant_id = generation.tenant_id
       AND artifact.generation_run_id = generation.id
       AND artifact.revision = 1
     FOR SHARE;
    IF NOT FOUND THEN
        RETURN false;
    END IF;

    PERFORM 1
      FROM app.course_generation_source_edges edge
     WHERE edge.tenant_id = generation.tenant_id
       AND edge.generation_run_id = generation.id
       AND edge.edge_kind = 'generated_lesson'
     FOR SHARE;
    IF NOT FOUND THEN
        RETURN false;
    END IF;
    RETURN true;
END
$$;
REVOKE ALL ON FUNCTION app.lock_generation_canonicalization_scope(uuid, uuid, bigint, text)
    FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app.lock_generation_canonicalization_scope(
    uuid,
    uuid,
    bigint,
    text
) TO lms_api_runtime;

CREATE TRIGGER trg_generation_canonicalizations_immutable
BEFORE UPDATE OR DELETE ON audit.course_generation_canonicalizations
FOR EACH ROW EXECUTE FUNCTION app.reject_generation_evidence_mutation();
CREATE TRIGGER trg_canonicalization_edges_immutable
BEFORE UPDATE OR DELETE ON app.course_generation_canonicalization_edges
FOR EACH ROW EXECUTE FUNCTION app.reject_generation_evidence_mutation();

ALTER TABLE audit.course_generation_canonicalizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit.course_generation_canonicalizations FORCE ROW LEVEL SECURITY;
CREATE POLICY generation_canonical_api_select
    ON audit.course_generation_canonicalizations
    FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'course_generation.runs.read'));
CREATE POLICY generation_canonical_api_insert
    ON audit.course_generation_canonicalizations
    FOR INSERT TO lms_api_runtime
    WITH CHECK (
        canonicalized_by_actor_id = app.current_actor_id()
        AND app.has_permission(tenant_id, 'course_generation.drafts.canonicalize')
        AND app.has_permission(tenant_id, 'courses.drafts.write')
    );

ALTER TABLE app.course_generation_canonicalization_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.course_generation_canonicalization_edges FORCE ROW LEVEL SECURITY;
CREATE POLICY canonical_edges_api_select
    ON app.course_generation_canonicalization_edges
    FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'course_generation.runs.read'));
CREATE POLICY canonical_edges_api_insert
    ON app.course_generation_canonicalization_edges
    FOR INSERT TO lms_api_runtime
    WITH CHECK (
        app.has_permission(tenant_id, 'course_generation.drafts.canonicalize')
        AND app.has_permission(tenant_id, 'courses.drafts.write')
        AND EXISTS (
            SELECT 1
             FROM audit.course_generation_canonicalizations canonicalization
             WHERE canonicalization.tenant_id = course_generation_canonicalization_edges.tenant_id
               AND canonicalization.id = course_generation_canonicalization_edges.canonicalization_id
               AND canonicalization.generation_run_id = course_generation_canonicalization_edges.generation_run_id
               AND canonicalization.course_id = course_generation_canonicalization_edges.course_id
               AND canonicalization.course_version_id = course_generation_canonicalization_edges.course_version_id
               AND canonicalization.canonicalized_by_actor_id = app.current_actor_id()
        )
    );

GRANT SELECT, INSERT ON audit.course_generation_canonicalizations,
    app.course_generation_canonicalization_edges TO lms_api_runtime;
"""


REVERSE_SQL = r"""
DROP TRIGGER IF EXISTS trg_generated_course_publication_rights ON app.course_versions;
DROP FUNCTION IF EXISTS app.guard_generated_course_publication();
DROP FUNCTION IF EXISTS app.lock_generated_course_publication(uuid, uuid, uuid);
DROP TRIGGER IF EXISTS trg_canonicalization_target_snapshot
    ON app.course_generation_canonicalization_edges;
DROP FUNCTION IF EXISTS app.validate_canonicalization_target_snapshot();
REVOKE ALL ON audit.course_generation_canonicalizations,
    app.course_generation_canonicalization_edges FROM lms_api_runtime, lms_worker_runtime;
REVOKE ALL ON FUNCTION app.lock_generation_canonicalization_scope(
    uuid,
    uuid,
    bigint,
    text
) FROM lms_api_runtime, lms_worker_runtime;

DROP POLICY IF EXISTS canonical_edges_api_insert
    ON app.course_generation_canonicalization_edges;
DROP POLICY IF EXISTS canonical_edges_api_select
    ON app.course_generation_canonicalization_edges;
DROP POLICY IF EXISTS generation_canonical_api_insert
    ON audit.course_generation_canonicalizations;
DROP POLICY IF EXISTS generation_canonical_api_select
    ON audit.course_generation_canonicalizations;

DROP TRIGGER IF EXISTS trg_canonicalization_edges_immutable
    ON app.course_generation_canonicalization_edges;
DROP TRIGGER IF EXISTS trg_generation_canonicalizations_immutable
    ON audit.course_generation_canonicalizations;

DROP FUNCTION IF EXISTS app.lock_generation_canonicalization_scope(
    uuid,
    uuid,
    bigint,
    text
);
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

ALTER TABLE app.course_generation_canonicalization_edges
    DROP CONSTRAINT IF EXISTS ck_canonical_edges_target_ids,
    DROP CONSTRAINT IF EXISTS fk_canonical_edges_same_tenant_version,
    DROP CONSTRAINT IF EXISTS fk_canonical_edges_same_tenant_course,
    DROP CONSTRAINT IF EXISTS fk_canonical_edges_same_tenant_section_source,
    DROP CONSTRAINT IF EXISTS fk_canonical_edges_same_tenant_version_source,
    DROP CONSTRAINT IF EXISTS fk_canonical_edges_same_tenant_artifact,
    DROP CONSTRAINT IF EXISTS fk_canonical_edges_same_tenant_run,
    DROP CONSTRAINT IF EXISTS fk_canonical_edges_same_tenant_canonical;
ALTER TABLE audit.course_generation_canonicalizations
    DROP CONSTRAINT IF EXISTS ck_generation_canonical_slug,
    DROP CONSTRAINT IF EXISTS fk_generation_canonical_same_tenant_version,
    DROP CONSTRAINT IF EXISTS fk_generation_canonical_same_tenant_course,
    DROP CONSTRAINT IF EXISTS fk_generation_canonical_same_tenant_run;
"""


class Migration(migrations.Migration):
    dependencies = [("course_generation", "0005_generationcanonicalization_and_more")]

    operations = [migrations.RunSQL(FORWARD_SQL, REVERSE_SQL)]
