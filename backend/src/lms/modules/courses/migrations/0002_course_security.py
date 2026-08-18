from __future__ import annotations

import uuid

from django.db import migrations

COURSE_PERMISSIONS = (
    ("courses.read", "Read tenant courses"),
    ("courses.drafts.write", "Create and edit tenant course drafts"),
    ("courses.review", "Review tenant course versions"),
    ("courses.publish", "Publish and withdraw tenant course versions"),
)
COURSE_ROLE_PERMISSIONS = {
    "tenant_admin": tuple(code for code, _ in COURSE_PERMISSIONS),
    "instructor": tuple(code for code, _ in COURSE_PERMISSIONS),
    "reviewer": ("courses.read", "courses.review"),
    "learner": (),
}


def seed_course_permissions(apps, schema_editor):
    del schema_editor
    Permission = apps.get_model("tenancy", "Permission")
    Role = apps.get_model("tenancy", "Role")
    RolePermission = apps.get_model("tenancy", "RolePermission")

    permissions = {}
    for code, description in COURSE_PERMISSIONS:
        permission, _ = Permission.objects.update_or_create(
            code=code,
            defaults={
                "id": uuid.uuid5(uuid.NAMESPACE_URL, f"ai-lms:permission:{code}"),
                "description": description,
            },
        )
        permissions[code] = permission

    for role in Role.objects.filter(code__in=COURSE_ROLE_PERMISSIONS):
        for permission_code in COURSE_ROLE_PERMISSIONS[role.code]:
            edge_id = uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"ai-lms:{role.tenant_id}:role-permission:{role.code}:{permission_code}",
            )
            RolePermission.objects.get_or_create(
                tenant_id=role.tenant_id,
                role_id=role.id,
                permission_id=permissions[permission_code].id,
                defaults={"id": edge_id},
            )


def unseed_course_permissions(apps, schema_editor):
    del schema_editor
    Permission = apps.get_model("tenancy", "Permission")
    RolePermission = apps.get_model("tenancy", "RolePermission")
    codes = tuple(code for code, _ in COURSE_PERMISSIONS)
    RolePermission.objects.filter(permission__code__in=codes).delete()
    Permission.objects.filter(code__in=codes).delete()


FORWARD_SQL = r"""
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

ALTER TABLE app.courses OWNER TO lms_object_owner;
ALTER TABLE app.course_versions OWNER TO lms_object_owner;
ALTER TABLE app.course_instructors OWNER TO lms_object_owner;
ALTER TABLE app.curriculum_sections OWNER TO lms_object_owner;
ALTER TABLE app.lessons OWNER TO lms_object_owner;
ALTER TABLE app.lesson_content_blocks OWNER TO lms_object_owner;
ALTER TABLE app.course_publication_reviews OWNER TO lms_object_owner;

REVOKE ALL ON app.courses, app.course_versions, app.course_instructors,
    app.curriculum_sections, app.lessons, app.lesson_content_blocks,
    app.course_publication_reviews FROM PUBLIC;

ALTER TABLE app.course_versions
    ADD CONSTRAINT fk_versions_same_tenant_course
    FOREIGN KEY (tenant_id, course_id)
    REFERENCES app.courses (tenant_id, id) ON DELETE RESTRICT;
ALTER TABLE app.course_versions
    ADD CONSTRAINT fk_versions_same_course_predecessor
    FOREIGN KEY (tenant_id, course_id, predecessor_version_id)
    REFERENCES app.course_versions (tenant_id, course_id, id) ON DELETE RESTRICT;
ALTER TABLE app.courses
    ADD CONSTRAINT fk_courses_current_version
    FOREIGN KEY (tenant_id, id, current_published_version_id)
    REFERENCES app.course_versions (tenant_id, course_id, id) ON DELETE RESTRICT;
ALTER TABLE app.course_instructors
    ADD CONSTRAINT fk_instructors_same_tenant_course
    FOREIGN KEY (tenant_id, course_id)
    REFERENCES app.courses (tenant_id, id) ON DELETE CASCADE;
ALTER TABLE app.course_instructors
    ADD CONSTRAINT fk_instructors_same_tenant_member
    FOREIGN KEY (tenant_id, membership_id)
    REFERENCES app.tenant_memberships (tenant_id, id) ON DELETE RESTRICT;
ALTER TABLE app.curriculum_sections
    ADD CONSTRAINT fk_sections_same_tenant_version
    FOREIGN KEY (tenant_id, course_version_id)
    REFERENCES app.course_versions (tenant_id, id) ON DELETE CASCADE;
ALTER TABLE app.lessons
    ADD CONSTRAINT fk_lessons_same_version_section
    FOREIGN KEY (tenant_id, course_version_id, section_id)
    REFERENCES app.curriculum_sections (tenant_id, course_version_id, id)
    ON DELETE CASCADE;
ALTER TABLE app.lesson_content_blocks
    ADD CONSTRAINT fk_blocks_same_version_lesson
    FOREIGN KEY (tenant_id, course_version_id, lesson_id)
    REFERENCES app.lessons (tenant_id, course_version_id, id) ON DELETE CASCADE;
ALTER TABLE app.course_publication_reviews
    ADD CONSTRAINT fk_reviews_same_tenant_version
    FOREIGN KEY (tenant_id, course_version_id)
    REFERENCES app.course_versions (tenant_id, id) ON DELETE RESTRICT;

ALTER TABLE app.lesson_content_blocks
    ADD CONSTRAINT ck_blocks_document_object
    CHECK (jsonb_typeof(document) = 'object');
ALTER TABLE app.course_publication_reviews
    ADD CONSTRAINT ck_reviews_reason_codes_array
    CHECK (jsonb_typeof(reason_codes) = 'array' AND jsonb_array_length(reason_codes) <= 20);

CREATE OR REPLACE FUNCTION app.enforce_course_identity_and_pointer()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, app
SET row_security = off
AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND (
        NEW.id IS DISTINCT FROM OLD.id
        OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
        OR NEW.slug IS DISTINCT FROM OLD.slug
    ) THEN
        RAISE EXCEPTION 'course identity is immutable' USING ERRCODE = '55000';
    END IF;

    IF NEW.current_published_version_id IS NOT NULL AND NOT EXISTS (
        SELECT 1
          FROM app.course_versions version
         WHERE version.tenant_id = NEW.tenant_id
           AND version.course_id = NEW.id
           AND version.id = NEW.current_published_version_id
           AND version.status = 'published'
    ) THEN
        RAISE EXCEPTION 'current course version must be a published version of this course'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION app.enforce_course_identity_and_pointer() FROM PUBLIC;

CREATE OR REPLACE FUNCTION app.enforce_course_version_mutability()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, app
SET row_security = off
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'course versions are retained as immutable history'
            USING ERRCODE = '55000';
    END IF;

    IF NEW.id IS DISTINCT FROM OLD.id
       OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
       OR NEW.course_id IS DISTINCT FROM OLD.course_id
       OR NEW.version_number IS DISTINCT FROM OLD.version_number
       OR NEW.predecessor_version_id IS DISTINCT FROM OLD.predecessor_version_id THEN
        RAISE EXCEPTION 'course version identity is immutable' USING ERRCODE = '55000';
    END IF;

    IF OLD.status NOT IN ('draft', 'changes_requested') AND (
        NEW.origin_type IS DISTINCT FROM OLD.origin_type
        OR NEW.primary_locale IS DISTINCT FROM OLD.primary_locale
        OR NEW.title IS DISTINCT FROM OLD.title
        OR NEW.description IS DISTINCT FROM OLD.description
        OR NEW.content_hash IS DISTINCT FROM OLD.content_hash
    ) THEN
        RAISE EXCEPTION 'course version content is immutable in state %', OLD.status
            USING ERRCODE = '55000';
    END IF;

    IF (
        session_user = 'lms_api_runtime'
        OR current_setting('role', true) = 'lms_api_runtime'
    ) AND NOT app.has_permission(OLD.tenant_id, 'courses.drafts.write') AND (
        NEW.origin_type IS DISTINCT FROM OLD.origin_type
        OR NEW.primary_locale IS DISTINCT FROM OLD.primary_locale
        OR NEW.title IS DISTINCT FROM OLD.title
        OR NEW.description IS DISTINCT FROM OLD.description
        OR NEW.content_hash IS DISTINCT FROM OLD.content_hash
    ) THEN
        RAISE EXCEPTION 'course draft permission is required for content mutation'
            USING ERRCODE = '42501';
    END IF;

    IF OLD.status IN ('published', 'withdrawn', 'archived') AND (
        NEW.submitted_hash IS DISTINCT FROM OLD.submitted_hash
        OR NEW.approved_hash IS DISTINCT FROM OLD.approved_hash
    ) THEN
        RAISE EXCEPTION 'published course review hashes are immutable'
            USING ERRCODE = '55000';
    END IF;

    IF (OLD.status = 'published' AND NEW.status NOT IN ('published', 'withdrawn'))
       OR (OLD.status = 'withdrawn' AND NEW.status NOT IN ('withdrawn', 'archived'))
       OR (OLD.status = 'archived' AND NEW.status <> 'archived') THEN
        RAISE EXCEPTION 'historical publication state cannot return to an editable lifecycle'
            USING ERRCODE = '55000';
    END IF;

    IF OLD.status = 'published' AND NEW.status <> 'published' AND EXISTS (
        SELECT 1
          FROM app.courses course
         WHERE course.tenant_id = OLD.tenant_id
           AND course.id = OLD.course_id
           AND course.current_published_version_id = OLD.id
    ) THEN
        RAISE EXCEPTION 'clear the current publication pointer before leaving published state'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION app.enforce_course_version_mutability() FROM PUBLIC;

CREATE OR REPLACE FUNCTION app.enforce_mutable_course_child()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, app
SET row_security = off
AS $$
DECLARE
    target_tenant_id uuid;
    target_version_id uuid;
    version_status text;
BEGIN
    IF TG_OP = 'DELETE' THEN
        target_tenant_id := OLD.tenant_id;
        target_version_id := OLD.course_version_id;
    ELSE
        target_tenant_id := NEW.tenant_id;
        target_version_id := NEW.course_version_id;
    END IF;

    IF TG_OP = 'UPDATE' AND (
        NEW.id IS DISTINCT FROM OLD.id
        OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
        OR NEW.course_version_id IS DISTINCT FROM OLD.course_version_id
        OR (TG_TABLE_NAME = 'lessons'
            AND to_jsonb(NEW)->>'section_id' IS DISTINCT FROM to_jsonb(OLD)->>'section_id')
        OR (TG_TABLE_NAME = 'lesson_content_blocks'
            AND to_jsonb(NEW)->>'lesson_id' IS DISTINCT FROM to_jsonb(OLD)->>'lesson_id')
    ) THEN
        RAISE EXCEPTION 'curriculum child identity is immutable' USING ERRCODE = '55000';
    END IF;

    SELECT status INTO version_status
      FROM app.course_versions
     WHERE tenant_id = target_tenant_id AND id = target_version_id;
    IF version_status IS NULL OR version_status NOT IN ('draft', 'changes_requested') THEN
        RAISE EXCEPTION 'course curriculum is immutable for this version'
            USING ERRCODE = '55000';
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END
$$;
REVOKE ALL ON FUNCTION app.enforce_mutable_course_child() FROM PUBLIC;

CREATE OR REPLACE FUNCTION app.reject_course_review_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    RAISE EXCEPTION 'course publication reviews are append-only' USING ERRCODE = '55000';
END
$$;
REVOKE ALL ON FUNCTION app.reject_course_review_mutation() FROM PUBLIC;

CREATE TRIGGER courses_identity_and_pointer
BEFORE INSERT OR UPDATE ON app.courses
FOR EACH ROW EXECUTE FUNCTION app.enforce_course_identity_and_pointer();
CREATE TRIGGER course_versions_mutability
BEFORE UPDATE OR DELETE ON app.course_versions
FOR EACH ROW EXECUTE FUNCTION app.enforce_course_version_mutability();
CREATE TRIGGER sections_version_mutability
BEFORE INSERT OR UPDATE OR DELETE ON app.curriculum_sections
FOR EACH ROW EXECUTE FUNCTION app.enforce_mutable_course_child();
CREATE TRIGGER lessons_version_mutability
BEFORE INSERT OR UPDATE OR DELETE ON app.lessons
FOR EACH ROW EXECUTE FUNCTION app.enforce_mutable_course_child();
CREATE TRIGGER blocks_version_mutability
BEFORE INSERT OR UPDATE OR DELETE ON app.lesson_content_blocks
FOR EACH ROW EXECUTE FUNCTION app.enforce_mutable_course_child();
CREATE TRIGGER course_reviews_immutable
BEFORE UPDATE OR DELETE ON app.course_publication_reviews
FOR EACH ROW EXECUTE FUNCTION app.reject_course_review_mutation();

ALTER TABLE app.courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.courses FORCE ROW LEVEL SECURITY;
CREATE POLICY courses_select ON app.courses FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'courses.read'));
CREATE POLICY courses_insert ON app.courses FOR INSERT TO lms_api_runtime
    WITH CHECK (app.has_permission(tenant_id, 'courses.drafts.write'));
CREATE POLICY courses_update ON app.courses FOR UPDATE TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'courses.drafts.write')
        OR app.has_permission(tenant_id, 'courses.publish')
    )
    WITH CHECK (
        app.has_permission(tenant_id, 'courses.drafts.write')
        OR app.has_permission(tenant_id, 'courses.publish')
    );

ALTER TABLE app.course_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.course_versions FORCE ROW LEVEL SECURITY;
CREATE POLICY course_versions_select ON app.course_versions FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'courses.read'));
CREATE POLICY course_versions_insert ON app.course_versions FOR INSERT TO lms_api_runtime
    WITH CHECK (app.has_permission(tenant_id, 'courses.drafts.write'));
CREATE POLICY course_versions_update ON app.course_versions FOR UPDATE TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'courses.drafts.write')
        OR app.has_permission(tenant_id, 'courses.review')
        OR app.has_permission(tenant_id, 'courses.publish')
    )
    WITH CHECK (
        app.has_permission(tenant_id, 'courses.drafts.write')
        OR app.has_permission(tenant_id, 'courses.review')
        OR app.has_permission(tenant_id, 'courses.publish')
    );

ALTER TABLE app.course_instructors ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.course_instructors FORCE ROW LEVEL SECURITY;
CREATE POLICY course_instructors_select ON app.course_instructors FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'courses.read'));
CREATE POLICY course_instructors_write ON app.course_instructors FOR ALL TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'courses.drafts.write'))
    WITH CHECK (app.has_permission(tenant_id, 'courses.drafts.write'));

ALTER TABLE app.curriculum_sections ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.curriculum_sections FORCE ROW LEVEL SECURITY;
CREATE POLICY sections_select ON app.curriculum_sections FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'courses.read'));
CREATE POLICY sections_write ON app.curriculum_sections FOR ALL TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'courses.drafts.write'))
    WITH CHECK (app.has_permission(tenant_id, 'courses.drafts.write'));

ALTER TABLE app.lessons ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.lessons FORCE ROW LEVEL SECURITY;
CREATE POLICY lessons_select ON app.lessons FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'courses.read'));
CREATE POLICY lessons_write ON app.lessons FOR ALL TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'courses.drafts.write'))
    WITH CHECK (app.has_permission(tenant_id, 'courses.drafts.write'));

ALTER TABLE app.lesson_content_blocks ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.lesson_content_blocks FORCE ROW LEVEL SECURITY;
CREATE POLICY blocks_select ON app.lesson_content_blocks FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'courses.read'));
CREATE POLICY blocks_write ON app.lesson_content_blocks FOR ALL TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'courses.drafts.write'))
    WITH CHECK (app.has_permission(tenant_id, 'courses.drafts.write'));

ALTER TABLE app.course_publication_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.course_publication_reviews FORCE ROW LEVEL SECURITY;
CREATE POLICY course_reviews_select ON app.course_publication_reviews
    FOR SELECT TO lms_api_runtime
    USING (app.has_permission(tenant_id, 'courses.read'));
CREATE POLICY course_reviews_insert ON app.course_publication_reviews
    FOR INSERT TO lms_api_runtime
    WITH CHECK (app.has_permission(tenant_id, 'courses.review'));

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

DROP POLICY audit_insert ON audit.tenant_audit_facts;
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

DROP POLICY outbox_insert ON integration.tenant_outbox_facts;
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

GRANT SELECT, INSERT, UPDATE ON app.courses, app.course_versions TO lms_api_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON app.course_instructors,
    app.curriculum_sections, app.lessons, app.lesson_content_blocks TO lms_api_runtime;
GRANT SELECT, INSERT ON app.course_publication_reviews TO lms_api_runtime;
"""


REVERSE_SQL = r"""
REVOKE ALL ON app.courses, app.course_versions, app.course_instructors,
    app.curriculum_sections, app.lessons, app.lesson_content_blocks,
    app.course_publication_reviews FROM lms_api_runtime;

DROP POLICY IF EXISTS course_reviews_insert ON app.course_publication_reviews;
DROP POLICY IF EXISTS course_reviews_select ON app.course_publication_reviews;
DROP POLICY IF EXISTS blocks_write ON app.lesson_content_blocks;
DROP POLICY IF EXISTS blocks_select ON app.lesson_content_blocks;
DROP POLICY IF EXISTS lessons_write ON app.lessons;
DROP POLICY IF EXISTS lessons_select ON app.lessons;
DROP POLICY IF EXISTS sections_write ON app.curriculum_sections;
DROP POLICY IF EXISTS sections_select ON app.curriculum_sections;
DROP POLICY IF EXISTS course_instructors_write ON app.course_instructors;
DROP POLICY IF EXISTS course_instructors_select ON app.course_instructors;
DROP POLICY IF EXISTS course_versions_update ON app.course_versions;
DROP POLICY IF EXISTS course_versions_insert ON app.course_versions;
DROP POLICY IF EXISTS course_versions_select ON app.course_versions;
DROP POLICY IF EXISTS courses_update ON app.courses;
DROP POLICY IF EXISTS courses_insert ON app.courses;
DROP POLICY IF EXISTS courses_select ON app.courses;

DROP POLICY IF EXISTS idempotency_all ON integration.idempotency_reservations;
CREATE POLICY idempotency_all ON integration.idempotency_reservations
    FOR ALL TO lms_api_runtime
    USING (
        actor_id = app.current_actor_id()
        AND app.has_permission(tenant_id, 'tenancy.invitations.create')
    )
    WITH CHECK (
        actor_id = app.current_actor_id()
        AND app.has_permission(tenant_id, 'tenancy.invitations.create')
    );
DROP POLICY IF EXISTS audit_insert ON audit.tenant_audit_facts;
CREATE POLICY audit_insert ON audit.tenant_audit_facts FOR INSERT TO lms_api_runtime
    WITH CHECK (
        tenant_id = app.current_tenant_id()
        AND (
            app.has_permission(tenant_id, 'tenancy.invitations.create')
            OR app.has_permission(tenant_id, 'tenancy.memberships.update')
            OR app.has_invitation_access(tenant_id)
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
        )
    );

DROP TRIGGER IF EXISTS course_reviews_immutable ON app.course_publication_reviews;
DROP TRIGGER IF EXISTS blocks_version_mutability ON app.lesson_content_blocks;
DROP TRIGGER IF EXISTS lessons_version_mutability ON app.lessons;
DROP TRIGGER IF EXISTS sections_version_mutability ON app.curriculum_sections;
DROP TRIGGER IF EXISTS course_versions_mutability ON app.course_versions;
DROP TRIGGER IF EXISTS courses_identity_and_pointer ON app.courses;
DROP FUNCTION IF EXISTS app.reject_course_review_mutation();
DROP FUNCTION IF EXISTS app.enforce_mutable_course_child();
DROP FUNCTION IF EXISTS app.enforce_course_version_mutability();
DROP FUNCTION IF EXISTS app.enforce_course_identity_and_pointer();

ALTER TABLE app.course_publication_reviews
    DROP CONSTRAINT IF EXISTS ck_reviews_reason_codes_array;
ALTER TABLE app.lesson_content_blocks DROP CONSTRAINT IF EXISTS ck_blocks_document_object;
ALTER TABLE app.course_publication_reviews
    DROP CONSTRAINT IF EXISTS fk_reviews_same_tenant_version;
ALTER TABLE app.lesson_content_blocks
    DROP CONSTRAINT IF EXISTS fk_blocks_same_version_lesson;
ALTER TABLE app.lessons DROP CONSTRAINT IF EXISTS fk_lessons_same_version_section;
ALTER TABLE app.curriculum_sections
    DROP CONSTRAINT IF EXISTS fk_sections_same_tenant_version;
ALTER TABLE app.course_instructors
    DROP CONSTRAINT IF EXISTS fk_instructors_same_tenant_member;
ALTER TABLE app.course_instructors
    DROP CONSTRAINT IF EXISTS fk_instructors_same_tenant_course;
ALTER TABLE app.courses DROP CONSTRAINT IF EXISTS fk_courses_current_version;
ALTER TABLE app.course_versions
    DROP CONSTRAINT IF EXISTS fk_versions_same_course_predecessor;
ALTER TABLE app.course_versions DROP CONSTRAINT IF EXISTS fk_versions_same_tenant_course;
"""


class Migration(migrations.Migration):
    dependencies = [("courses", "0001_initial")]

    operations = [
        migrations.RunPython(seed_course_permissions, unseed_course_permissions),
        migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL),
    ]
