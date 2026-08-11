from django.db import migrations

FORWARD_SQL = """
DO $roles$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lms_object_owner') THEN
        CREATE ROLE lms_object_owner
            NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lms_api_runtime') THEN
        CREATE ROLE lms_api_runtime
            LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
    END IF;
END
$roles$;

CREATE SCHEMA IF NOT EXISTS app AUTHORIZATION lms_object_owner;
CREATE SCHEMA IF NOT EXISTS audit AUTHORIZATION lms_object_owner;
CREATE SCHEMA IF NOT EXISTS governance AUTHORIZATION lms_object_owner;
CREATE SCHEMA IF NOT EXISTS integration AUTHORIZATION lms_object_owner;

REVOKE ALL ON SCHEMA app, audit, governance, integration FROM PUBLIC;
GRANT USAGE ON SCHEMA app TO lms_api_runtime;
"""

REVERSE_SQL = """
REVOKE ALL ON SCHEMA app FROM lms_api_runtime;
DROP SCHEMA IF EXISTS integration RESTRICT;
DROP SCHEMA IF EXISTS governance RESTRICT;
DROP SCHEMA IF EXISTS audit RESTRICT;
DROP SCHEMA IF EXISTS app RESTRICT;
DROP ROLE IF EXISTS lms_api_runtime;
DROP ROLE IF EXISTS lms_object_owner;
"""


class Migration(migrations.Migration):
    initial = True
    dependencies: list[tuple[str, str]] = []
    operations = [migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL)]
