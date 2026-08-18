from __future__ import annotations

from typing import Any

import pytest

from lms.modules.courses.models import (
    COURSE_VERSION_STATUSES,
    Course,
    CourseInstructor,
    CourseVersion,
    CurriculumSection,
    Lesson,
    LessonContentBlock,
)
from lms.modules.tenancy.models import RolePermission
from tests.tenancy.conftest import tenancy_seed as tenancy_seed

CONTENT_HASH = "sha256:" + "1" * 64
DOCUMENT = {
    "type": "document",
    "content": [
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": "Synthetic course text.", "marks": []}],
        }
    ],
}


def create_course_graph(seed: dict[str, Any], tenant_key: str = "alpha") -> dict[str, Any]:
    tenant = seed[tenant_key]
    membership_key = "instructor_alpha" if tenant_key == "alpha" else "instructor_beta"
    course = Course.objects.create(tenant=tenant, slug=f"{tenant_key}-course")
    version = CourseVersion.objects.create(
        tenant=tenant,
        course=course,
        version_number=1,
        primary_locale="en",
        title="Synthetic course",
        description="Rights-cleared synthetic fixture.",
        content_hash=CONTENT_HASH,
    )
    instructor = CourseInstructor.objects.create(
        tenant=tenant,
        course=course,
        membership=seed["memberships"][membership_key],
    )
    section = CurriculumSection.objects.create(
        tenant=tenant,
        course_version=version,
        title="Section one",
        position=1,
    )
    lesson = Lesson.objects.create(
        tenant=tenant,
        course_version=version,
        section=section,
        title="Lesson one",
        position=1,
        is_required=True,
    )
    block = LessonContentBlock.objects.create(
        tenant=tenant,
        course_version=version,
        lesson=lesson,
        position=1,
        document=DOCUMENT,
    )
    return {
        "course": course,
        "version": version,
        "instructor": instructor,
        "section": section,
        "lesson": lesson,
        "block": block,
    }


def test_course_models_use_the_frozen_tables_and_states() -> None:
    assert {
        Course._meta.db_table,
        CourseVersion._meta.db_table,
        CourseInstructor._meta.db_table,
        CurriculumSection._meta.db_table,
        Lesson._meta.db_table,
        LessonContentBlock._meta.db_table,
    } == {
        'app"."courses',
        'app"."course_versions',
        'app"."course_instructors',
        'app"."curriculum_sections',
        'app"."lessons',
        'app"."lesson_content_blocks',
    }
    assert COURSE_VERSION_STATUSES == (
        "draft",
        "under_review",
        "changes_requested",
        "approved",
        "scheduled",
        "published",
        "withdrawn",
        "archived",
    )


@pytest.mark.django_db
def test_fixed_course_permission_matrix_is_provisioned(tenancy_seed: dict[str, Any]) -> None:
    expected = {
        "tenant_admin": {
            "courses.read",
            "courses.drafts.write",
            "courses.review",
            "courses.publish",
        },
        "instructor": {
            "courses.read",
            "courses.drafts.write",
            "courses.review",
            "courses.publish",
        },
        "reviewer": {"courses.read", "courses.review"},
        "learner": set(),
    }
    for role_code, permission_codes in expected.items():
        actual = set(
            RolePermission.objects.filter(
                tenant=tenancy_seed["alpha"],
                role__code=role_code,
                permission__code__startswith="courses.",
            ).values_list("permission__code", flat=True)
        )
        assert actual == permission_codes
