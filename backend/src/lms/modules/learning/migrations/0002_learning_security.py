from __future__ import annotations

import uuid

from django.db import migrations

LEARNING_PERMISSIONS = {
    "learning.enrollments.manage": "Create and revoke manual learner enrollments",
    "learning.playback.read": "Read own enrolled courses and record progress",
}
ROLE_PERMISSION_CODES = {
    "tenant_admin": ("learning.enrollments.manage",),
    "instructor": (),
    "reviewer": (),
    "learner": ("learning.playback.read",),
}


def seed_learning_permissions(apps, schema_editor):
    del schema_editor
    Permission = apps.get_model("tenancy", "Permission")
    Role = apps.get_model("tenancy", "Role")
    RolePermission = apps.get_model("tenancy", "RolePermission")
    permissions = {}
    for code, description in LEARNING_PERMISSIONS.items():
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


def unseed_learning_permissions(apps, schema_editor):
    del schema_editor
    Permission = apps.get_model("tenancy", "Permission")
    RolePermission = apps.get_model("tenancy", "RolePermission")
    permission_ids = list(
        Permission.objects.filter(code__in=LEARNING_PERMISSIONS).values_list("id", flat=True)
    )
    RolePermission.objects.filter(permission_id__in=permission_ids).delete()
    Permission.objects.filter(id__in=permission_ids).delete()


FORWARD_SQL = r"""
SET lock_timeout = '5s';
SET statement_timeout = '30s';

ALTER TABLE app.enrollments OWNER TO lms_object_owner;
ALTER TABLE app.course_progress OWNER TO lms_object_owner;
ALTER TABLE app.lesson_progress OWNER TO lms_object_owner;

REVOKE ALL ON app.enrollments, app.course_progress, app.lesson_progress FROM PUBLIC;

ALTER TABLE app.enrollments
    ADD CONSTRAINT fk_enrollments_same_tenant_membership
    FOREIGN KEY (tenant_id, learner_membership_id)
    REFERENCES app.tenant_memberships (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_enrollments_same_tenant_course
    FOREIGN KEY (tenant_id, course_id)
    REFERENCES app.courses (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_enrollments_same_course_version
    FOREIGN KEY (tenant_id, course_id, course_version_id)
    REFERENCES app.course_versions (tenant_id, course_id, id) ON DELETE RESTRICT;

ALTER TABLE app.course_progress
    ADD CONSTRAINT fk_course_progress_same_tenant_enrollment
    FOREIGN KEY (tenant_id, enrollment_id)
    REFERENCES app.enrollments (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_course_progress_same_tenant_version
    FOREIGN KEY (tenant_id, course_version_id)
    REFERENCES app.course_versions (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_course_progress_same_version_resume
    FOREIGN KEY (tenant_id, course_version_id, resume_lesson_id)
    REFERENCES app.lessons (tenant_id, course_version_id, id) ON DELETE RESTRICT;

ALTER TABLE app.lesson_progress
    ADD CONSTRAINT fk_lesson_progress_same_tenant_enrollment
    FOREIGN KEY (tenant_id, enrollment_id)
    REFERENCES app.enrollments (tenant_id, id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_lesson_progress_same_version_lesson
    FOREIGN KEY (tenant_id, course_version_id, lesson_id)
    REFERENCES app.lessons (tenant_id, course_version_id, id) ON DELETE RESTRICT;

CREATE OR REPLACE FUNCTION app.enforce_enrollment_lifecycle()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'enrollment history is retained' USING ERRCODE = '55000';
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id
       OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
       OR NEW.learner_membership_id IS DISTINCT FROM OLD.learner_membership_id
       OR NEW.course_id IS DISTINCT FROM OLD.course_id
       OR NEW.course_version_id IS DISTINCT FROM OLD.course_version_id
       OR NEW.admission_source IS DISTINCT FROM OLD.admission_source
       OR NEW.enrolled_at IS DISTINCT FROM OLD.enrolled_at
       OR NEW.assigned_by_actor_id IS DISTINCT FROM OLD.assigned_by_actor_id
       OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'enrollment identity and version pin are immutable'
            USING ERRCODE = '55000';
    END IF;
    IF OLD.status <> 'active' OR NEW.status <> 'revoked' THEN
        RAISE EXCEPTION 'enrollment revocation is the only update'
            USING ERRCODE = '23514';
    END IF;
    IF NEW.row_version <> OLD.row_version + 1 THEN
        RAISE EXCEPTION 'enrollment transition requires the next row version'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION app.enforce_enrollment_lifecycle() FROM PUBLIC;

CREATE OR REPLACE FUNCTION app.enforce_course_progress_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'course progress is retained' USING ERRCODE = '55000';
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id
       OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
       OR NEW.enrollment_id IS DISTINCT FROM OLD.enrollment_id
       OR NEW.course_version_id IS DISTINCT FROM OLD.course_version_id
       OR NEW.required_lesson_count IS DISTINCT FROM OLD.required_lesson_count
       OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'course progress scope is immutable' USING ERRCODE = '55000';
    END IF;
    IF NEW.state = 'not_started' AND OLD.state <> 'not_started' THEN
        RAISE EXCEPTION 'course progress cannot return to not_started'
            USING ERRCODE = '23514';
    END IF;
    IF NEW.row_version <> OLD.row_version + 1 THEN
        RAISE EXCEPTION 'course progress requires the next row version'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION app.enforce_course_progress_mutation() FROM PUBLIC;

CREATE OR REPLACE FUNCTION app.enforce_lesson_progress_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'lesson progress is retained' USING ERRCODE = '55000';
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id
       OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
       OR NEW.enrollment_id IS DISTINCT FROM OLD.enrollment_id
       OR NEW.course_version_id IS DISTINCT FROM OLD.course_version_id
       OR NEW.lesson_id IS DISTINCT FROM OLD.lesson_id
       OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'lesson progress scope is immutable' USING ERRCODE = '55000';
    END IF;
    IF NEW.state = 'not_started' AND OLD.state <> 'not_started' THEN
        RAISE EXCEPTION 'lesson progress cannot return to not_started'
            USING ERRCODE = '23514';
    END IF;
    IF NEW.row_version <> OLD.row_version + 1 THEN
        RAISE EXCEPTION 'lesson progress requires the next row version'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION app.enforce_lesson_progress_mutation() FROM PUBLIC;

CREATE TRIGGER enrollments_terminal_lifecycle
BEFORE UPDATE OR DELETE ON app.enrollments
FOR EACH ROW EXECUTE FUNCTION app.enforce_enrollment_lifecycle();
CREATE TRIGGER course_progress_lifecycle
BEFORE UPDATE OR DELETE ON app.course_progress
FOR EACH ROW EXECUTE FUNCTION app.enforce_course_progress_mutation();
CREATE TRIGGER lesson_progress_lifecycle
BEFORE UPDATE OR DELETE ON app.lesson_progress
FOR EACH ROW EXECUTE FUNCTION app.enforce_lesson_progress_mutation();

CREATE OR REPLACE FUNCTION app.has_active_learning_enrollment(
    target_tenant_id uuid,
    target_enrollment_id uuid
)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, app
SET row_security = off
AS $$
    SELECT target_tenant_id = app.current_tenant_id()
       AND app.has_permission(target_tenant_id, 'learning.playback.read')
       AND EXISTS (
            SELECT 1
              FROM app.enrollments enrollment
              JOIN app.tenant_memberships membership
                ON membership.tenant_id = enrollment.tenant_id
               AND membership.id = enrollment.learner_membership_id
              JOIN app.course_versions version
                ON version.tenant_id = enrollment.tenant_id
               AND version.id = enrollment.course_version_id
             WHERE enrollment.tenant_id = target_tenant_id
               AND enrollment.id = target_enrollment_id
               AND enrollment.status = 'active'
               AND membership.status = 'active'
               AND membership.user_profile_id = app.current_user_profile_id()
               AND version.status = 'published'
       )
$$;

CREATE OR REPLACE FUNCTION app.has_learning_version_access(
    target_tenant_id uuid,
    target_course_version_id uuid
)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, app
SET row_security = off
AS $$
    SELECT target_tenant_id = app.current_tenant_id()
       AND app.has_permission(target_tenant_id, 'learning.playback.read')
       AND EXISTS (
            SELECT 1
              FROM app.enrollments enrollment
              JOIN app.tenant_memberships membership
                ON membership.tenant_id = enrollment.tenant_id
               AND membership.id = enrollment.learner_membership_id
              JOIN app.course_versions version
                ON version.tenant_id = enrollment.tenant_id
               AND version.id = enrollment.course_version_id
             WHERE enrollment.tenant_id = target_tenant_id
               AND enrollment.course_version_id = target_course_version_id
               AND enrollment.status = 'active'
               AND membership.status = 'active'
               AND membership.user_profile_id = app.current_user_profile_id()
               AND version.status = 'published'
       )
$$;

CREATE OR REPLACE FUNCTION app.has_learning_course_access(
    target_tenant_id uuid,
    target_course_id uuid
)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, app
SET row_security = off
AS $$
    SELECT target_tenant_id = app.current_tenant_id()
       AND app.has_permission(target_tenant_id, 'learning.playback.read')
       AND EXISTS (
            SELECT 1
              FROM app.enrollments enrollment
              JOIN app.tenant_memberships membership
                ON membership.tenant_id = enrollment.tenant_id
               AND membership.id = enrollment.learner_membership_id
              JOIN app.course_versions version
                ON version.tenant_id = enrollment.tenant_id
               AND version.id = enrollment.course_version_id
             WHERE enrollment.tenant_id = target_tenant_id
               AND enrollment.course_id = target_course_id
               AND enrollment.status = 'active'
               AND membership.status = 'active'
               AND membership.user_profile_id = app.current_user_profile_id()
               AND version.status = 'published'
       )
$$;

CREATE OR REPLACE FUNCTION app.lock_active_learning_membership(
    target_tenant_id uuid,
    target_membership_id uuid
)
RETURNS boolean
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog, app
SET row_security = off
AS $$
DECLARE
    allowed boolean := false;
BEGIN
    SELECT target_tenant_id = app.current_tenant_id()
       AND membership.user_profile_id = app.current_user_profile_id()
       AND membership.status = 'active'
       AND app.has_permission(target_tenant_id, 'learning.playback.read')
      INTO allowed
      FROM app.tenant_memberships membership
     WHERE membership.tenant_id = target_tenant_id
       AND membership.id = target_membership_id
     FOR SHARE;
    RETURN COALESCE(allowed, false);
END
$$;

REVOKE ALL ON FUNCTION app.has_active_learning_enrollment(uuid, uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION app.has_learning_version_access(uuid, uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION app.has_learning_course_access(uuid, uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION app.lock_active_learning_membership(uuid, uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app.has_active_learning_enrollment(uuid, uuid)
    TO lms_api_runtime;
GRANT EXECUTE ON FUNCTION app.has_learning_version_access(uuid, uuid)
    TO lms_api_runtime;
GRANT EXECUTE ON FUNCTION app.has_learning_course_access(uuid, uuid)
    TO lms_api_runtime;
GRANT EXECUTE ON FUNCTION app.lock_active_learning_membership(uuid, uuid)
    TO lms_api_runtime;

ALTER TABLE app.enrollments ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.enrollments FORCE ROW LEVEL SECURITY;
CREATE POLICY enrollments_select ON app.enrollments FOR SELECT TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'learning.enrollments.manage')
        OR app.has_active_learning_enrollment(tenant_id, id)
    );
CREATE POLICY enrollments_insert ON app.enrollments FOR INSERT TO lms_api_runtime
    WITH CHECK (app.has_permission(tenant_id, 'learning.enrollments.manage'));
CREATE POLICY enrollments_update ON app.enrollments FOR UPDATE TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'learning.enrollments.manage')
        OR app.has_active_learning_enrollment(tenant_id, id)
    )
    WITH CHECK (
        app.has_permission(tenant_id, 'learning.enrollments.manage')
        OR app.has_active_learning_enrollment(tenant_id, id)
    );

ALTER TABLE app.course_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.course_progress FORCE ROW LEVEL SECURITY;
CREATE POLICY course_progress_select ON app.course_progress FOR SELECT TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'learning.enrollments.manage')
        OR app.has_active_learning_enrollment(tenant_id, enrollment_id)
    );
CREATE POLICY course_progress_insert ON app.course_progress FOR INSERT TO lms_api_runtime
    WITH CHECK (app.has_active_learning_enrollment(tenant_id, enrollment_id));
CREATE POLICY course_progress_update ON app.course_progress FOR UPDATE TO lms_api_runtime
    USING (app.has_active_learning_enrollment(tenant_id, enrollment_id))
    WITH CHECK (app.has_active_learning_enrollment(tenant_id, enrollment_id));

ALTER TABLE app.lesson_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.lesson_progress FORCE ROW LEVEL SECURITY;
CREATE POLICY lesson_progress_select ON app.lesson_progress FOR SELECT TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'learning.enrollments.manage')
        OR app.has_active_learning_enrollment(tenant_id, enrollment_id)
    );
CREATE POLICY lesson_progress_insert ON app.lesson_progress FOR INSERT TO lms_api_runtime
    WITH CHECK (app.has_active_learning_enrollment(tenant_id, enrollment_id));
CREATE POLICY lesson_progress_update ON app.lesson_progress FOR UPDATE TO lms_api_runtime
    USING (app.has_active_learning_enrollment(tenant_id, enrollment_id))
    WITH CHECK (app.has_active_learning_enrollment(tenant_id, enrollment_id));

CREATE POLICY courses_learning_select ON app.courses FOR SELECT TO lms_api_runtime
    USING (app.has_learning_course_access(tenant_id, id));
CREATE POLICY course_versions_learning_select ON app.course_versions
    FOR SELECT TO lms_api_runtime
    USING (app.has_learning_version_access(tenant_id, id));
CREATE POLICY sections_learning_select ON app.curriculum_sections
    FOR SELECT TO lms_api_runtime
    USING (app.has_learning_version_access(tenant_id, course_version_id));
CREATE POLICY lessons_learning_select ON app.lessons FOR SELECT TO lms_api_runtime
    USING (app.has_learning_version_access(tenant_id, course_version_id));
CREATE POLICY blocks_learning_select ON app.lesson_content_blocks
    FOR SELECT TO lms_api_runtime
    USING (app.has_learning_version_access(tenant_id, course_version_id));

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
            OR app.has_permission(tenant_id, 'learning.enrollments.manage')
            OR app.has_permission(tenant_id, 'learning.playback.read')
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
            OR app.has_permission(tenant_id, 'learning.enrollments.manage')
            OR app.has_permission(tenant_id, 'learning.playback.read')
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
            OR app.has_permission(tenant_id, 'learning.enrollments.manage')
            OR app.has_permission(tenant_id, 'learning.playback.read')
        ))
        OR app.has_upload_intent_scope(tenant_id, subject_id)
        OR app.has_service_job_scope(tenant_id, subject_id, app.current_job_stage())
    );

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
            OR app.has_permission(tenant_id, 'learning.enrollments.manage')
            OR app.has_permission(tenant_id, 'learning.playback.read')
        ))
        OR app.has_upload_intent_scope(tenant_id, aggregate_id)
        OR app.has_service_job_scope(tenant_id, aggregate_id, app.current_job_stage())
    );

GRANT SELECT, INSERT, UPDATE ON app.enrollments, app.course_progress,
    app.lesson_progress TO lms_api_runtime;
"""


REVERSE_SQL = r"""
REVOKE ALL ON app.enrollments, app.course_progress, app.lesson_progress
    FROM lms_api_runtime;

DROP POLICY IF EXISTS blocks_learning_select ON app.lesson_content_blocks;
DROP POLICY IF EXISTS lessons_learning_select ON app.lessons;
DROP POLICY IF EXISTS sections_learning_select ON app.curriculum_sections;
DROP POLICY IF EXISTS course_versions_learning_select ON app.course_versions;
DROP POLICY IF EXISTS courses_learning_select ON app.courses;
DROP POLICY IF EXISTS lesson_progress_update ON app.lesson_progress;
DROP POLICY IF EXISTS lesson_progress_insert ON app.lesson_progress;
DROP POLICY IF EXISTS lesson_progress_select ON app.lesson_progress;
DROP POLICY IF EXISTS course_progress_update ON app.course_progress;
DROP POLICY IF EXISTS course_progress_insert ON app.course_progress;
DROP POLICY IF EXISTS course_progress_select ON app.course_progress;
DROP POLICY IF EXISTS enrollments_update ON app.enrollments;
DROP POLICY IF EXISTS enrollments_insert ON app.enrollments;
DROP POLICY IF EXISTS enrollments_select ON app.enrollments;

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
DROP POLICY IF EXISTS audit_insert ON audit.tenant_audit_facts;
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
DROP POLICY IF EXISTS outbox_insert ON integration.tenant_outbox_facts;
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

DROP FUNCTION IF EXISTS app.has_learning_course_access(uuid, uuid);
DROP FUNCTION IF EXISTS app.has_learning_version_access(uuid, uuid);
DROP FUNCTION IF EXISTS app.has_active_learning_enrollment(uuid, uuid);
DROP FUNCTION IF EXISTS app.lock_active_learning_membership(uuid, uuid);
DROP TRIGGER IF EXISTS lesson_progress_lifecycle ON app.lesson_progress;
DROP TRIGGER IF EXISTS course_progress_lifecycle ON app.course_progress;
DROP TRIGGER IF EXISTS enrollments_terminal_lifecycle ON app.enrollments;
DROP FUNCTION IF EXISTS app.enforce_lesson_progress_mutation();
DROP FUNCTION IF EXISTS app.enforce_course_progress_mutation();
DROP FUNCTION IF EXISTS app.enforce_enrollment_lifecycle();

ALTER TABLE app.lesson_progress
    DROP CONSTRAINT IF EXISTS fk_lesson_progress_same_version_lesson,
    DROP CONSTRAINT IF EXISTS fk_lesson_progress_same_tenant_enrollment;
ALTER TABLE app.course_progress
    DROP CONSTRAINT IF EXISTS fk_course_progress_same_version_resume,
    DROP CONSTRAINT IF EXISTS fk_course_progress_same_tenant_version,
    DROP CONSTRAINT IF EXISTS fk_course_progress_same_tenant_enrollment;
ALTER TABLE app.enrollments
    DROP CONSTRAINT IF EXISTS fk_enrollments_same_course_version,
    DROP CONSTRAINT IF EXISTS fk_enrollments_same_tenant_course,
    DROP CONSTRAINT IF EXISTS fk_enrollments_same_tenant_membership;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0001_initial"),
        ("documents", "0002_document_security"),
    ]

    operations = [
        migrations.RunPython(seed_learning_permissions, unseed_learning_permissions),
        migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL),
    ]
