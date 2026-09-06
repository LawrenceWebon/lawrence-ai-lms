from __future__ import annotations

from django.db import connection

from lms.modules.courses.types import CourseSnapshot


class GenerationPublicationSources:
    """Recheck immutable lineage and lock current rights inside the Courses command."""

    def allows_publication(self, snapshot: CourseSnapshot) -> bool:
        if not connection.in_atomic_block:
            return False
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT app.lock_generated_course_publication(%s, %s, %s)",
                [
                    str(snapshot.course.tenant_id),
                    str(snapshot.course.id),
                    str(snapshot.version.id),
                ],
            )
            result = cursor.fetchone()
        return result is not None and result[0] is True
