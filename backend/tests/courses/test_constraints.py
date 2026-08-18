from __future__ import annotations

from typing import Any

import pytest
from django.db import DatabaseError, IntegrityError, transaction
from django.utils import timezone

from lms.modules.courses.models import (
    Course,
    CourseInstructor,
    CoursePublicationReview,
    CourseVersion,
    CurriculumSection,
    Lesson,
    LessonContentBlock,
)
from tests.courses.test_models import CONTENT_HASH, DOCUMENT, create_course_graph
from tests.tenancy.conftest import tenancy_seed as tenancy_seed


@pytest.mark.django_db
def test_every_parent_edge_rejects_cross_tenant_or_wrong_parent(
    tenancy_seed: dict[str, Any],
) -> None:
    alpha = create_course_graph(tenancy_seed, "alpha")
    beta = create_course_graph(tenancy_seed, "beta")

    with pytest.raises(IntegrityError), transaction.atomic():
        CourseVersion.objects.create(
            tenant=tenancy_seed["beta"],
            course=alpha["course"],
            version_number=2,
            primary_locale="en",
            title="Wrong tenant",
            description="Synthetic.",
            content_hash=CONTENT_HASH,
        )

    other_course = Course.objects.create(tenant=tenancy_seed["alpha"], slug="other-course")
    with pytest.raises(IntegrityError), transaction.atomic():
        CourseVersion.objects.create(
            tenant=tenancy_seed["alpha"],
            course=other_course,
            predecessor_version=alpha["version"],
            version_number=1,
            primary_locale="en",
            title="Wrong predecessor",
            description="Synthetic.",
            content_hash=CONTENT_HASH,
        )

    with pytest.raises(IntegrityError), transaction.atomic():
        CourseInstructor.objects.create(
            tenant=tenancy_seed["alpha"],
            course=alpha["course"],
            membership=tenancy_seed["memberships"]["instructor_beta"],
        )

    with pytest.raises(DatabaseError), transaction.atomic():
        CurriculumSection.objects.create(
            tenant=tenancy_seed["alpha"],
            course_version=beta["version"],
            title="Wrong tenant",
            position=2,
        )

    with pytest.raises(DatabaseError), transaction.atomic():
        Lesson.objects.create(
            tenant=tenancy_seed["alpha"],
            course_version=alpha["version"],
            section=beta["section"],
            title="Wrong parent",
            position=2,
        )

    with pytest.raises(DatabaseError), transaction.atomic():
        LessonContentBlock.objects.create(
            tenant=tenancy_seed["alpha"],
            course_version=alpha["version"],
            lesson=beta["lesson"],
            position=2,
            document=DOCUMENT,
        )

    with pytest.raises(DatabaseError), transaction.atomic():
        CoursePublicationReview.objects.create(
            tenant=tenancy_seed["alpha"],
            course_version=beta["version"],
            decision="approved",
            reviewed_hash=CONTENT_HASH,
            reviewer_id=tenancy_seed["profiles"]["instructor"].provider_subject,
            decided_at=timezone.now(),
        )

    other_version = CourseVersion.objects.create(
        tenant=tenancy_seed["alpha"],
        course=other_course,
        version_number=1,
        status="published",
        primary_locale="en",
        title="Other published course",
        description="Synthetic.",
        content_hash=CONTENT_HASH,
        submitted_hash=CONTENT_HASH,
        approved_hash=CONTENT_HASH,
    )
    with pytest.raises(DatabaseError), transaction.atomic():
        Course.objects.filter(id=alpha["course"].id).update(
            current_published_version_id=other_version.id
        )


@pytest.mark.django_db
def test_slug_version_and_ordered_positions_are_tenant_safe_and_unique(
    tenancy_seed: dict[str, Any],
) -> None:
    graph = create_course_graph(tenancy_seed)
    with pytest.raises(IntegrityError), transaction.atomic():
        Course.objects.create(tenant=tenancy_seed["alpha"], slug="alpha-course")
    assert (
        Course.objects.create(tenant=tenancy_seed["beta"], slug="alpha-course").tenant_id
        == tenancy_seed["beta"].id
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        CourseVersion.objects.create(
            tenant=tenancy_seed["alpha"],
            course=graph["course"],
            version_number=1,
            primary_locale="en",
            title="Duplicate",
            description="Synthetic.",
            content_hash=CONTENT_HASH,
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        CurriculumSection.objects.create(
            tenant=tenancy_seed["alpha"],
            course_version=graph["version"],
            title="Duplicate position",
            position=1,
        )


@pytest.mark.django_db
def test_publication_pointer_requires_this_courses_published_version(
    tenancy_seed: dict[str, Any],
) -> None:
    graph = create_course_graph(tenancy_seed)
    course = graph["course"]
    version = graph["version"]
    course.current_published_version = version
    with pytest.raises(DatabaseError), transaction.atomic():
        course.save(update_fields=("current_published_version", "updated_at"))

    CourseVersion.objects.filter(id=version.id).update(
        status="published",
        submitted_hash=CONTENT_HASH,
        approved_hash=CONTENT_HASH,
    )
    course.refresh_from_db()
    course.current_published_version_id = version.id
    course.save(update_fields=("current_published_version", "updated_at"))
    assert Course.objects.get(id=course.id).current_published_version_id == version.id


@pytest.mark.django_db
def test_published_content_children_and_review_facts_are_immutable(
    tenancy_seed: dict[str, Any],
) -> None:
    graph = create_course_graph(tenancy_seed)
    version = graph["version"]
    CourseVersion.objects.filter(id=version.id).update(
        status="published",
        submitted_hash=CONTENT_HASH,
        approved_hash=CONTENT_HASH,
    )
    with pytest.raises(DatabaseError), transaction.atomic():
        CourseVersion.objects.filter(id=version.id).update(title="Mutated")
    with pytest.raises(DatabaseError), transaction.atomic():
        CourseVersion.objects.filter(id=version.id).update(status="draft")
    with pytest.raises(DatabaseError), transaction.atomic():
        CurriculumSection.objects.filter(id=graph["section"].id).update(title="Mutated")
    with pytest.raises(DatabaseError), transaction.atomic():
        Lesson.objects.filter(id=graph["lesson"].id).delete()

    review = CoursePublicationReview.objects.create(
        tenant=tenancy_seed["alpha"],
        course_version=version,
        decision="approved",
        reviewed_hash=CONTENT_HASH,
        reviewer_id=tenancy_seed["profiles"]["instructor"].provider_subject,
        decided_at=timezone.now(),
    )
    with pytest.raises(DatabaseError), transaction.atomic():
        CoursePublicationReview.objects.filter(id=review.id).update(self_review=True)
    with pytest.raises(DatabaseError), transaction.atomic():
        CoursePublicationReview.objects.filter(id=review.id).delete()

    CourseVersion.objects.filter(id=version.id).update(status="withdrawn")
    with pytest.raises(DatabaseError), transaction.atomic():
        LessonContentBlock.objects.filter(id=graph["block"].id).update(position=2)
    CourseVersion.objects.filter(id=version.id).update(status="archived")
    with pytest.raises(DatabaseError), transaction.atomic():
        CurriculumSection.objects.filter(id=graph["section"].id).delete()
