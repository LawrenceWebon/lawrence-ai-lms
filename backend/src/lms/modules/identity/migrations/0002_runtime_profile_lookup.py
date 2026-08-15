from django.db import migrations

FORWARD_SQL = """
CREATE OR REPLACE FUNCTION app.identity_profile_for_subject(target_subject uuid)
RETURNS TABLE(id uuid, provider_subject uuid, status varchar)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, app
SET row_security = off
AS $$
    SELECT profile.id, profile.provider_subject, profile.status
      FROM app.user_profiles profile
     WHERE profile.provider_subject = target_subject
     LIMIT 1
$$;

REVOKE ALL ON FUNCTION app.identity_profile_for_subject(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app.identity_profile_for_subject(uuid) TO lms_api_runtime;
"""

REVERSE_SQL = """
DROP FUNCTION IF EXISTS app.identity_profile_for_subject(uuid);
"""


class Migration(migrations.Migration):
    dependencies = [("lms_identity", "0001_initial")]
    operations = [migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL)]
