from django.db import migrations

FORWARD_SQL = r"""
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

DROP POLICY enrollments_update ON app.enrollments;
CREATE POLICY enrollments_update ON app.enrollments FOR UPDATE TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'learning.enrollments.manage')
        OR app.has_active_learning_enrollment(tenant_id, id)
    )
    WITH CHECK (app.has_permission(tenant_id, 'learning.enrollments.manage'));
"""

REVERSE_SQL = r"""
DROP POLICY enrollments_update ON app.enrollments;
CREATE POLICY enrollments_update ON app.enrollments FOR UPDATE TO lms_api_runtime
    USING (
        app.has_permission(tenant_id, 'learning.enrollments.manage')
        OR app.has_active_learning_enrollment(tenant_id, id)
    )
    WITH CHECK (
        app.has_permission(tenant_id, 'learning.enrollments.manage')
        OR app.has_active_learning_enrollment(tenant_id, id)
    );
"""


class Migration(migrations.Migration):
    dependencies = [("learning", "0002_learning_security")]
    operations = [migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL)]
