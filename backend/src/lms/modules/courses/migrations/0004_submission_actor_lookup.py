from django.db import migrations

FORWARD_SQL = """
CREATE FUNCTION app.course_submission_actor(p_tenant_id uuid, p_version_id uuid)
RETURNS uuid
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog
SET row_security = off
AS $$
    SELECT fact.actor_id
      FROM audit.tenant_audit_facts fact
      JOIN app.course_versions version
        ON version.tenant_id = fact.tenant_id AND version.id = fact.subject_id
     WHERE fact.tenant_id = p_tenant_id
       AND fact.subject_id = p_version_id
       AND fact.subject_type = 'course_version'
       AND fact.event_type = 'course.version.submitted.v1'
       AND app.current_tenant_id() = p_tenant_id
       AND app.has_permission(p_tenant_id, 'courses.read')
     ORDER BY fact.occurred_at DESC, fact.id DESC
     LIMIT 1
$$;
REVOKE ALL ON FUNCTION app.course_submission_actor(uuid, uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app.course_submission_actor(uuid, uuid) TO lms_api_runtime;
"""


class Migration(migrations.Migration):
    dependencies = [("courses", "0003_one_successor")]
    operations = [
        migrations.RunSQL(
            FORWARD_SQL,
            "DROP FUNCTION IF EXISTS app.course_submission_actor(uuid, uuid);",
        )
    ]
