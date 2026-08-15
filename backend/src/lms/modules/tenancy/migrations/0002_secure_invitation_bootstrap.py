from django.db import migrations

FORWARD_SQL = """
CREATE OR REPLACE FUNCTION app.has_invitation_identity_match(target_tenant_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, app
SET row_security = off
AS $$
    SELECT app.current_actor_id() IS NOT NULL
       AND NULLIF(current_setting('app.current_verified_email', true), '') IS NOT NULL
       AND EXISTS (
            SELECT 1
              FROM app.tenant_invitations invitation
              JOIN app.tenants tenant ON tenant.id = invitation.tenant_id
             WHERE invitation.tenant_id = target_tenant_id
               AND invitation.token_digest =
                   NULLIF(current_setting('app.current_invitation_digest', true), '')
               AND invitation.email =
                   lower(btrim(NULLIF(current_setting('app.current_verified_email', true), '')))
               AND tenant.status = 'active'
               AND EXISTS (
                    SELECT 1
                      FROM app.entitlement_periods entitlement
                     WHERE entitlement.tenant_id = invitation.tenant_id
                       AND entitlement.status = 'active'
                       AND entitlement.starts_at <= transaction_timestamp()
                       AND (entitlement.valid_until IS NULL
                            OR entitlement.valid_until > transaction_timestamp())
               )
       )
$$;

CREATE OR REPLACE FUNCTION app.has_invitation_access(target_tenant_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, app
SET row_security = off
AS $$
    SELECT app.has_invitation_identity_match(target_tenant_id)
       AND EXISTS (
            SELECT 1
              FROM app.tenant_invitations invitation
             WHERE invitation.tenant_id = target_tenant_id
               AND invitation.token_digest =
                   NULLIF(current_setting('app.current_invitation_digest', true), '')
               AND invitation.status IN ('active', 'accepted')
       )
$$;

REVOKE ALL ON FUNCTION app.has_invitation_identity_match(uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION app.has_invitation_access(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app.has_invitation_identity_match(uuid) TO lms_api_runtime;
GRANT EXECUTE ON FUNCTION app.has_invitation_access(uuid) TO lms_api_runtime;

DROP POLICY invitations_select ON app.tenant_invitations;
CREATE POLICY invitations_select ON app.tenant_invitations FOR SELECT TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'tenancy.invitations.create')
        OR app.has_invitation_access(tenant_id)
        OR (status = 'expired' AND app.has_invitation_identity_match(tenant_id))
    );

DROP POLICY invitations_update ON app.tenant_invitations;
CREATE POLICY invitations_update ON app.tenant_invitations FOR UPDATE TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'tenancy.invitations.create')
        OR app.has_invitation_access(tenant_id)
    )
    WITH CHECK (
        app.has_permission(tenant_id, 'tenancy.invitations.create')
        OR app.has_invitation_access(tenant_id)
        OR (status = 'expired' AND app.has_invitation_identity_match(tenant_id))
    );
"""

REVERSE_SQL = """
DROP POLICY invitations_select ON app.tenant_invitations;
CREATE POLICY invitations_select ON app.tenant_invitations FOR SELECT TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'tenancy.invitations.create')
        OR app.has_invitation_access(tenant_id)
    );

DROP POLICY invitations_update ON app.tenant_invitations;
CREATE POLICY invitations_update ON app.tenant_invitations FOR UPDATE TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'tenancy.invitations.create')
        OR app.has_invitation_access(tenant_id)
    )
    WITH CHECK (
        app.has_permission(tenant_id, 'tenancy.invitations.create')
        OR app.has_invitation_access(tenant_id)
    );

CREATE OR REPLACE FUNCTION app.has_invitation_access(target_tenant_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, app
SET row_security = off
AS $$
    SELECT app.current_actor_id() IS NOT NULL
       AND EXISTS (
            SELECT 1
              FROM app.tenant_invitations invitation
             WHERE invitation.tenant_id = target_tenant_id
               AND invitation.token_digest =
                   NULLIF(current_setting('app.current_invitation_digest', true), '')
               AND invitation.status IN ('active', 'accepted')
       )
$$;

DROP FUNCTION IF EXISTS app.has_invitation_identity_match(uuid);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("lms_identity", "0002_runtime_profile_lookup"),
        ("tenancy", "0001_initial"),
    ]
    operations = [migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL)]
