from __future__ import annotations

from typing import Any

import pytest

from lms.api.learning_composition import DjangoLearningFacts, DjangoLearningService
from lms.api.schemas.learning import (
    CreateEnrollmentV1,
    LearningAdministrationError,
    ProgressCommandV1,
    RevokeEnrollmentV1,
)
from lms.modules.learning.models import CourseProgress, Enrollment, LessonProgress
from lms.modules.tenancy.models import AuditFact, IdempotencyReservation, OutboxFact
from tests.learning.test_models import create_published_course
from tests.tenancy.conftest import tenancy_seed as tenancy_seed


@pytest.mark.django_db(transaction=True)
def test_real_learning_composition_assigns_reads_progresses_and_revokes_atomically(
    tenancy_seed: dict[str, Any],
) -> None:
    graph = create_published_course(tenancy_seed)
    service = DjangoLearningService()
    tenant_id = tenancy_seed["alpha"].id
    admin_actor_id = tenancy_seed["profiles"]["admin"].provider_subject
    learner_actor_id = tenancy_seed["profiles"]["learner"].provider_subject
    learner_membership_id = tenancy_seed["memberships"]["learner"].id
    create = CreateEnrollmentV1(
        learner_membership_id=learner_membership_id,
        course_id=graph["course"].id,
    )

    assigned = service.create_enrollment(
        actor_id=admin_actor_id,
        tenant_id=tenant_id,
        command=create,
        idempotency_key="assign-learning-0000001",
    )
    replay = service.create_enrollment(
        actor_id=admin_actor_id,
        tenant_id=tenant_id,
        command=create,
        idempotency_key="assign-learning-0000001",
    )

    assert replay == assigned
    assert assigned.course_version_id == graph["version"].id
    assert Enrollment.objects.count() == 1
    assert AuditFact.objects.filter(event_type="learning.enrollment.created.v1").count() == 1
    assert OutboxFact.objects.filter(event_type="learning.enrollment.created.v1").count() == 1

    dashboard = service.list_learner_courses(
        actor_id=learner_actor_id,
        tenant_id=tenant_id,
        cursor=None,
        limit=20,
    )
    playback = service.get_learner_playback(
        actor_id=learner_actor_id,
        tenant_id=tenant_id,
        enrollment_id=assigned.id,
    )
    lesson = service.get_learner_lesson(
        actor_id=learner_actor_id,
        tenant_id=tenant_id,
        enrollment_id=assigned.id,
        lesson_id=graph["lesson"].id,
    )
    assert dashboard.items[0].enrollment_id == assigned.id
    assert playback.course_version_id == graph["version"].id
    assert lesson.lesson.content_blocks[0].document["type"] == "document"
    assert CourseProgress.objects.count() == 0
    assert LessonProgress.objects.count() == 0

    completed = service.complete_lesson(
        actor_id=learner_actor_id,
        tenant_id=tenant_id,
        enrollment_id=assigned.id,
        command=ProgressCommandV1(
            command="complete_lesson",
            lesson_id=graph["lesson"].id,
            expected_progress_row_version=0,
        ),
        idempotency_key="complete-learning-00001",
    )
    assert completed.course_state.value == "completed"
    assert completed.progress_row_version == 1
    assert set(
        OutboxFact.objects.filter(event_type__startswith="learning.").values_list(
            "event_type", flat=True
        )
    ) == {
        "learning.enrollment.created.v1",
        "learning.lesson.progressed.v1",
        "learning.course.completed.v1",
    }
    assert all(
        "title" not in fact.payload and "description" not in fact.payload
        for fact in OutboxFact.objects.filter(event_type__startswith="learning.")
    )

    revoked = service.revoke_enrollment(
        actor_id=admin_actor_id,
        tenant_id=tenant_id,
        enrollment_id=assigned.id,
        command=RevokeEnrollmentV1(
            expected_enrollment_row_version=1,
            reason_code="ADMIN_REVOKED",
        ),
        idempotency_key="revoke-learning-000001",
    )
    assert revoked.status.value == "revoked"
    with pytest.raises(LearningAdministrationError) as caught:
        service.get_learner_playback(
            actor_id=learner_actor_id,
            tenant_id=tenant_id,
            enrollment_id=assigned.id,
        )
    assert caught.value.code == "LEARNING_RESOURCE_NOT_FOUND"


@pytest.mark.django_db(transaction=True)
def test_changed_idempotency_request_conflicts_without_a_second_effect(
    tenancy_seed: dict[str, Any],
) -> None:
    graph = create_published_course(tenancy_seed)
    service = DjangoLearningService()
    common = {
        "actor_id": tenancy_seed["profiles"]["admin"].provider_subject,
        "tenant_id": tenancy_seed["alpha"].id,
        "idempotency_key": "assign-learning-0000002",
    }
    service.create_enrollment(
        **common,
        command=CreateEnrollmentV1(
            learner_membership_id=tenancy_seed["memberships"]["learner"].id,
            course_id=graph["course"].id,
        ),
    )

    with pytest.raises(LearningAdministrationError) as caught:
        service.create_enrollment(
            **common,
            command=CreateEnrollmentV1(
                learner_membership_id=tenancy_seed["memberships"]["inactive"].id,
                course_id=graph["course"].id,
            ),
        )

    assert caught.value.code == "IDEMPOTENCY_CONFLICT"
    assert Enrollment.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_fact_failure_rolls_back_enrollment_reservation_and_all_facts(
    tenancy_seed: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = create_published_course(tenancy_seed)

    def fail_facts(self: DjangoLearningFacts, *facts: object) -> None:
        del self, facts
        raise RuntimeError("synthetic fact failure")

    monkeypatch.setattr(DjangoLearningFacts, "append", fail_facts)
    service = DjangoLearningService()
    with pytest.raises(RuntimeError, match="synthetic fact failure"):
        service.create_enrollment(
            actor_id=tenancy_seed["profiles"]["admin"].provider_subject,
            tenant_id=tenancy_seed["alpha"].id,
            command=CreateEnrollmentV1(
                learner_membership_id=tenancy_seed["memberships"]["learner"].id,
                course_id=graph["course"].id,
            ),
            idempotency_key="assign-learning-rollback",
        )

    assert Enrollment.objects.count() == 0
    assert (
        IdempotencyReservation.objects.filter(operation="learning.create_enrollment").count() == 0
    )
    assert AuditFact.objects.filter(event_type__startswith="learning.").count() == 0
    assert OutboxFact.objects.filter(event_type__startswith="learning.").count() == 0
