from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace

import pytest

from lms.modules.courses.errors import CourseLifecycleError
from lms.modules.courses.hashing import canonical_content_hash
from lms.modules.courses.types import (
    CourseStatus,
    CreateAiAssistedDraftCommand,
    CreateCourseCommand,
    CreateSuccessorDraftCommand,
    OriginType,
    PrincipalType,
    ReviewerPolicy,
    Transition,
    TransitionCourseVersionCommand,
    UpdateCourseVersionCommand,
)
from tests.contract_fakes.f002_courses import (
    ALPHA_AUTHOR_ID,
    ALPHA_REVIEWER_ID,
    ALPHA_SERVICE_ID,
    ALPHA_TENANT_ID,
    BETA_TENANT_ID,
    CourseServiceHarness,
    new_curriculum_command,
)


def _create(harness: CourseServiceHarness, *, key: str = "create-course-key-0001") -> object:
    return harness.service.create_course(
        actor_id=ALPHA_AUTHOR_ID,
        tenant_id=ALPHA_TENANT_ID,
        command=CreateCourseCommand(
            slug="synthetic-safe-learning",
            primary_locale="en",
            title="Synthetic Safe Learning",
            description="An invented course fixture.",
        ),
        idempotency_key=key,
    )


def _with_curriculum(harness: CourseServiceHarness) -> object:
    created = _create(harness)
    return harness.service.replace_curriculum(
        actor_id=ALPHA_AUTHOR_ID,
        tenant_id=ALPHA_TENANT_ID,
        course_id=created.course.id,
        version_id=created.version.id,
        command=new_curriculum_command(expected_version_row_version=created.version.row_version),
    )


def _transition(
    harness: CourseServiceHarness,
    snapshot: object,
    transition: Transition,
    key: str,
    *,
    actor_id: object = ALPHA_AUTHOR_ID,
    expected_hash: str | None = None,
    reason_code: str | None = None,
    reason_codes: tuple[str, ...] = (),
) -> object:
    return harness.service.transition_version(
        actor_id=actor_id,
        tenant_id=ALPHA_TENANT_ID,
        course_id=snapshot.course.id,
        version_id=snapshot.version.id,
        command=TransitionCourseVersionCommand(
            transition=transition,
            expected_version_row_version=snapshot.version.row_version,
            expected_content_hash=expected_hash or canonical_content_hash(snapshot),
            expected_course_row_version=(
                snapshot.course.row_version
                if transition in {Transition.PUBLISH, Transition.WITHDRAW}
                else None
            ),
            reason_code=reason_code,
            reason_codes=reason_codes,
        ),
        idempotency_key=key,
    )


def _approved(harness: CourseServiceHarness) -> object:
    draft = _with_curriculum(harness)
    submitted = _transition(harness, draft, Transition.SUBMIT_REVIEW, "submit-key-00000001")
    return _transition(harness, submitted, Transition.APPROVE, "approve-key-0000001")


def _published(harness: CourseServiceHarness) -> object:
    approved = _approved(harness)
    return _transition(harness, approved, Transition.PUBLISH, "publish-key-0000001")


def test_create_is_atomic_idempotent_and_server_derives_reviewer_policy() -> None:
    harness = CourseServiceHarness(reviewer_policy=ReviewerPolicy.SEPARATE_REVIEWER_REQUIRED)
    first = _create(harness)
    replay = _create(harness)

    assert replay == first
    assert first.course.reviewer_policy is ReviewerPolicy.SEPARATE_REVIEWER_REQUIRED
    assert first.course.instructor_membership_ids == (harness.author_membership_id,)
    assert harness.repository.version_count == 1

    with pytest.raises(CourseLifecycleError, match="IDEMPOTENCY_CONFLICT"):
        harness.service.create_course(
            actor_id=ALPHA_AUTHOR_ID,
            tenant_id=ALPHA_TENANT_ID,
            command=CreateCourseCommand("changed", "en", "Changed", "Changed description"),
            idempotency_key="create-course-key-0001",
        )


def test_ai_assisted_draft_command_creates_one_editable_unpublished_course_atomically() -> None:
    harness = CourseServiceHarness()
    curriculum = new_curriculum_command(section_count=2)
    command = CreateAiAssistedDraftCommand(
        slug="synthetic-ai-assisted",
        primary_locale="en",
        title="Synthetic AI-assisted course",
        description="A source-grounded synthetic draft.",
        sections=curriculum.sections,
    )
    created = harness.service.create_ai_assisted_draft(
        actor_id=ALPHA_AUTHOR_ID,
        tenant_id=ALPHA_TENANT_ID,
        command=command,
        idempotency_key="ai-assisted-draft-key-0001",
    )
    replay = harness.service.create_ai_assisted_draft(
        actor_id=ALPHA_AUTHOR_ID,
        tenant_id=ALPHA_TENANT_ID,
        command=command,
        idempotency_key="ai-assisted-draft-key-0001",
    )

    assert replay == created
    assert created.version.origin_type is OriginType.AI_ASSISTED
    assert created.version.status is CourseStatus.DRAFT
    assert created.course.current_published_version_id is None
    assert created.version.submitted_hash is None
    assert created.version.approved_hash is None
    assert len(created.sections) == 2
    assert harness.repository.version_count == 1


def test_update_and_replace_enforce_versions_and_increment_only_changed_children() -> None:
    harness = CourseServiceHarness()
    initial = _with_curriculum(harness)
    preserved = harness.preserve_curriculum(initial)
    unchanged = harness.service.replace_curriculum(
        actor_id=ALPHA_AUTHOR_ID,
        tenant_id=ALPHA_TENANT_ID,
        course_id=initial.course.id,
        version_id=initial.version.id,
        command=replace(preserved, expected_version_row_version=initial.version.row_version),
    )
    assert unchanged.version.row_version == initial.version.row_version + 1
    assert unchanged.sections[0].row_version == initial.sections[0].row_version
    assert (
        unchanged.sections[0].lessons[0].row_version == initial.sections[0].lessons[0].row_version
    )

    changed_command = harness.preserve_curriculum(unchanged, lesson_title="Changed lesson")
    changed = harness.service.replace_curriculum(
        actor_id=ALPHA_AUTHOR_ID,
        tenant_id=ALPHA_TENANT_ID,
        course_id=unchanged.course.id,
        version_id=unchanged.version.id,
        command=changed_command,
    )
    assert changed.sections[0].row_version == unchanged.sections[0].row_version
    assert (
        changed.sections[0].lessons[0].row_version
        == unchanged.sections[0].lessons[0].row_version + 1
    )

    with pytest.raises(CourseLifecycleError, match="VERSION_CONFLICT"):
        harness.service.update_version(
            actor_id=ALPHA_AUTHOR_ID,
            tenant_id=ALPHA_TENANT_ID,
            course_id=changed.course.id,
            version_id=changed.version.id,
            command=UpdateCourseVersionCommand(
                expected_version_row_version=initial.version.row_version,
                title="Stale title",
            ),
        )


def test_wrong_tenant_and_guessed_child_ids_fail_neutrally() -> None:
    harness = CourseServiceHarness()
    snapshot = _with_curriculum(harness)

    with pytest.raises(CourseLifecycleError, match="RESOURCE_NOT_FOUND"):
        harness.service.get_course_version(
            actor_id=ALPHA_AUTHOR_ID,
            tenant_id=BETA_TENANT_ID,
            course_id=snapshot.course.id,
            version_id=snapshot.version.id,
        )

    command = harness.preserve_curriculum(snapshot)
    guessed = replace(command.sections[0], id=harness.ids.new_uuid())
    with pytest.raises(CourseLifecycleError, match="RESOURCE_NOT_FOUND"):
        harness.service.replace_curriculum(
            actor_id=ALPHA_AUTHOR_ID,
            tenant_id=ALPHA_TENANT_ID,
            course_id=snapshot.course.id,
            version_id=snapshot.version.id,
            command=replace(command, sections=(guessed,)),
        )


def test_resource_scope_is_rederived_for_each_course_operation() -> None:
    harness = CourseServiceHarness()
    snapshot = _with_curriculum(harness)
    harness.authorization.deny_course(ALPHA_AUTHOR_ID, ALPHA_TENANT_ID, snapshot.course.id)

    with pytest.raises(CourseLifecycleError, match="RESOURCE_NOT_FOUND"):
        harness.service.get_course_version(
            actor_id=ALPHA_AUTHOR_ID,
            tenant_id=ALPHA_TENANT_ID,
            course_id=snapshot.course.id,
            version_id=snapshot.version.id,
        )


def test_submit_request_changes_edit_resubmit_approve_and_publish_exact_hash() -> None:
    harness = CourseServiceHarness()
    draft = _with_curriculum(harness)
    submitted = _transition(harness, draft, Transition.SUBMIT_REVIEW, "submit-key-00000001")
    assert submitted.version.submitted_hash == canonical_content_hash(submitted)

    changes = _transition(
        harness,
        submitted,
        Transition.REQUEST_CHANGES,
        "changes-key-0000001",
        reason_codes=("CONTENT_GAP",),
    )
    assert changes.latest_review is not None
    assert changes.latest_review.decision == "changes_requested"

    edited = harness.service.update_version(
        actor_id=ALPHA_AUTHOR_ID,
        tenant_id=ALPHA_TENANT_ID,
        course_id=changes.course.id,
        version_id=changes.version.id,
        command=UpdateCourseVersionCommand(
            expected_version_row_version=changes.version.row_version,
            title="Synthetic Safe Learning revised",
        ),
    )
    assert edited.version.submitted_hash is None
    assert edited.version.approved_hash is None

    resubmitted = _transition(harness, edited, Transition.SUBMIT_REVIEW, "resubmit-key-000001")
    approved = _transition(harness, resubmitted, Transition.APPROVE, "approve-key-0000001")
    assert approved.latest_review is not None
    assert approved.latest_review.self_review is True
    assert approved.version.approved_hash == canonical_content_hash(approved)
    assert harness.facts.outbox[-1].payload["self_review"] is True
    assert [
        review.decision
        for review in harness.repository.reviews_for(
            ALPHA_TENANT_ID, approved.course.id, approved.version.id
        )
    ] == ["changes_requested", "approved"]

    published = _transition(harness, approved, Transition.PUBLISH, "publish-key-0000001")
    assert published.version.status == "published"
    assert published.course.current_published_version_id == published.version.id
    assert harness.facts.outbox[-1].event_type == "course.version.published.v1"
    assert "title" not in harness.facts.outbox[-1].payload
    assert "description" not in harness.facts.outbox[-1].payload


def test_transitions_recompute_content_and_reject_hash_mismatch() -> None:
    harness = CourseServiceHarness()
    draft = _with_curriculum(harness)

    with pytest.raises(CourseLifecycleError, match="CONTENT_HASH_MISMATCH"):
        _transition(
            harness,
            draft,
            Transition.SUBMIT_REVIEW,
            "bad-hash-key-000001",
            expected_hash=f"sha256:{'0' * 64}",
        )


def test_separate_reviewer_policy_and_nonhuman_publication_fail_closed() -> None:
    harness = CourseServiceHarness(reviewer_policy=ReviewerPolicy.SEPARATE_REVIEWER_REQUIRED)
    draft = _with_curriculum(harness)
    submitted = _transition(harness, draft, Transition.SUBMIT_REVIEW, "submit-key-00000001")

    with pytest.raises(CourseLifecycleError, match="REVIEWER_SEPARATION_REQUIRED"):
        _transition(harness, submitted, Transition.APPROVE, "self-approve-key-001")

    approved = _transition(
        harness,
        submitted,
        Transition.APPROVE,
        "reviewer-approve-001",
        actor_id=ALPHA_REVIEWER_ID,
    )
    with pytest.raises(CourseLifecycleError, match="HUMAN_ACTION_REQUIRED"):
        _transition(
            harness,
            approved,
            Transition.PUBLISH,
            "service-publish-001",
            actor_id=ALPHA_SERVICE_ID,
        )


def test_same_key_replays_one_effect_and_changed_request_conflicts() -> None:
    harness = CourseServiceHarness()
    draft = _with_curriculum(harness)
    submitted = _transition(harness, draft, Transition.SUBMIT_REVIEW, "submit-key-00000001")
    fact_count = len(harness.facts.outbox)
    replay = _transition(harness, draft, Transition.SUBMIT_REVIEW, "submit-key-00000001")

    assert replay == submitted
    assert len(harness.facts.outbox) == fact_count

    with pytest.raises(CourseLifecycleError, match="IDEMPOTENCY_CONFLICT"):
        _transition(
            harness,
            draft,
            Transition.SUBMIT_REVIEW,
            "submit-key-00000001",
            expected_hash=f"sha256:{'1' * 64}",
        )


def test_publish_state_pointer_audit_idempotency_and_outbox_roll_back_together() -> None:
    harness = CourseServiceHarness()
    approved = _approved(harness)
    before = deepcopy(
        harness.repository.load_required(ALPHA_TENANT_ID, approved.course.id, approved.version.id)
    )
    before_audit = len(harness.facts.audit)
    before_outbox = len(harness.facts.outbox)
    harness.facts.fail_event_type = "course.version.published.v1"

    with pytest.raises(RuntimeError, match="injected fact failure"):
        _transition(harness, approved, Transition.PUBLISH, "rollback-publish-001")

    assert (
        harness.repository.load_required(ALPHA_TENANT_ID, approved.course.id, approved.version.id)
        == before
    )
    assert len(harness.facts.audit) == before_audit
    assert len(harness.facts.outbox) == before_outbox
    assert not harness.idempotency.is_completed("rollback-publish-001")


def test_simultaneous_publish_has_exactly_one_winner() -> None:
    harness = CourseServiceHarness()
    approved = _approved(harness)

    def publish(key: str) -> str:
        try:
            _transition(harness, approved, Transition.PUBLISH, key)
            return "published"
        except CourseLifecycleError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(publish, ("concurrent-publish-1", "concurrent-publish-2")))

    assert results.count("published") == 1
    assert len(results) == 2
    assert next(result for result in results if result != "published") in {
        "VERSION_CONFLICT",
        "COURSE_VERSION_IMMUTABLE",
    }


def test_simultaneous_metadata_updates_have_exactly_one_winner() -> None:
    harness = CourseServiceHarness()
    snapshot = _with_curriculum(harness)

    def update(title: str) -> str:
        try:
            harness.service.update_version(
                actor_id=ALPHA_AUTHOR_ID,
                tenant_id=ALPHA_TENANT_ID,
                course_id=snapshot.course.id,
                version_id=snapshot.version.id,
                command=UpdateCourseVersionCommand(snapshot.version.row_version, title=title),
            )
            return "updated"
        except CourseLifecycleError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(update, ("Winning title A", "Winning title B")))

    assert results.count("updated") == 1
    assert results.count("VERSION_CONFLICT") == 1


def test_complete_list_reorder_is_atomic_and_stale_competitor_loses() -> None:
    harness = CourseServiceHarness()
    created = _create(harness)
    snapshot = harness.service.replace_curriculum(
        actor_id=ALPHA_AUTHOR_ID,
        tenant_id=ALPHA_TENANT_ID,
        course_id=created.course.id,
        version_id=created.version.id,
        command=new_curriculum_command(
            expected_version_row_version=created.version.row_version,
            section_count=2,
        ),
    )
    preserved = harness.preserve_curriculum(snapshot)
    reordered = replace(
        preserved,
        sections=(
            replace(preserved.sections[0], position=2),
            replace(preserved.sections[1], position=1),
        ),
    )

    def reorder(command: object) -> str:
        try:
            harness.service.replace_curriculum(
                actor_id=ALPHA_AUTHOR_ID,
                tenant_id=ALPHA_TENANT_ID,
                course_id=snapshot.course.id,
                version_id=snapshot.version.id,
                command=command,
            )
            return "reordered"
        except CourseLifecycleError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(reorder, (reordered, preserved)))

    assert results.count("reordered") == 1
    assert results.count("VERSION_CONFLICT") == 1
    current = harness.service.get_course_version(
        actor_id=ALPHA_AUTHOR_ID,
        tenant_id=ALPHA_TENANT_ID,
        course_id=snapshot.course.id,
        version_id=snapshot.version.id,
    )
    assert {section.id for section in current.sections} == {
        section.id for section in snapshot.sections
    }
    assert [section.position for section in current.sections] == [1, 2]


def test_simultaneous_approval_has_one_review_and_one_winner() -> None:
    harness = CourseServiceHarness()
    draft = _with_curriculum(harness)
    submitted = _transition(harness, draft, Transition.SUBMIT_REVIEW, "submit-key-00000001")

    def approve(key: str) -> str:
        try:
            _transition(harness, submitted, Transition.APPROVE, key)
            return "approved"
        except CourseLifecycleError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(approve, ("concurrent-approve-1", "concurrent-approve-2")))

    assert results.count("approved") == 1
    assert (
        len(
            harness.repository.reviews_for(
                ALPHA_TENANT_ID, submitted.course.id, submitted.version.id
            )
        )
        == 1
    )


def test_published_content_rejects_metadata_and_curriculum_mutation() -> None:
    harness = CourseServiceHarness()
    published = _published(harness)

    with pytest.raises(CourseLifecycleError, match="COURSE_VERSION_IMMUTABLE"):
        harness.service.update_version(
            actor_id=ALPHA_AUTHOR_ID,
            tenant_id=ALPHA_TENANT_ID,
            course_id=published.course.id,
            version_id=published.version.id,
            command=UpdateCourseVersionCommand(
                published.version.row_version,
                title="Forbidden published edit",
            ),
        )
    with pytest.raises(CourseLifecycleError, match="COURSE_VERSION_IMMUTABLE"):
        harness.service.replace_curriculum(
            actor_id=ALPHA_AUTHOR_ID,
            tenant_id=ALPHA_TENANT_ID,
            course_id=published.course.id,
            version_id=published.version.id,
            command=harness.preserve_curriculum(published),
        )


def test_withdraw_and_archive_clear_the_pointer_and_emit_safe_reason_facts() -> None:
    harness = CourseServiceHarness()
    published = _published(harness)

    withdrawn = _transition(
        harness,
        published,
        Transition.WITHDRAW,
        "withdraw-key-000001",
        reason_code="CONTENT_RETIRED",
    )
    assert withdrawn.version.status == "withdrawn"
    assert withdrawn.course.current_published_version_id is None
    assert harness.facts.outbox[-1].event_type == "course.version.withdrawn.v1"
    assert harness.facts.outbox[-1].payload["reason_code"] == "CONTENT_RETIRED"

    archived = _transition(
        harness,
        withdrawn,
        Transition.ARCHIVE,
        "archive-key-0000001",
        reason_code="RETENTION_READY",
    )
    assert archived.version.status == "archived"
    assert harness.facts.outbox[-1].event_type == "course.version.archived.v1"
    assert harness.facts.outbox[-1].payload["reason_code"] == "RETENTION_READY"


def test_successor_draft_preserves_published_snapshot_and_resets_identity_and_review() -> None:
    harness = CourseServiceHarness()
    published = _published(harness)
    frozen = deepcopy(published)
    command = CreateSuccessorDraftCommand(
        expected_course_row_version=published.course.row_version,
        expected_source_version_row_version=published.version.row_version,
        expected_source_content_hash=canonical_content_hash(published),
    )
    result = harness.service.create_successor_draft(
        actor_id=ALPHA_AUTHOR_ID,
        tenant_id=ALPHA_TENANT_ID,
        course_id=published.course.id,
        source_version_id=published.version.id,
        command=command,
        idempotency_key="successor-key-000001",
    )
    replay = harness.service.create_successor_draft(
        actor_id=ALPHA_AUTHOR_ID,
        tenant_id=ALPHA_TENANT_ID,
        course_id=published.course.id,
        source_version_id=published.version.id,
        command=command,
        idempotency_key="successor-key-000001",
    )
    equivalent_replay = harness.service.create_successor_draft(
        actor_id=ALPHA_AUTHOR_ID,
        tenant_id=ALPHA_TENANT_ID,
        course_id=published.course.id,
        source_version_id=published.version.id,
        command=command,
        idempotency_key="successor-key-000002",
    )

    assert replay == result
    assert equivalent_replay == result
    assert result.snapshot.version.status == "draft"
    assert result.snapshot.version.predecessor_version_id == published.version.id
    assert result.snapshot.version.submitted_hash is None
    assert result.snapshot.version.approved_hash is None
    assert result.snapshot.latest_review is None
    assert result.snapshot.version.row_version == 1
    assert result.snapshot.sections[0].id != published.sections[0].id
    assert canonical_content_hash(result.snapshot) == canonical_content_hash(published)
    assert (
        harness.service.get_course_version(
            actor_id=ALPHA_AUTHOR_ID,
            tenant_id=ALPHA_TENANT_ID,
            course_id=published.course.id,
            version_id=published.version.id,
        ).version
        == frozen.version
    )

    history = harness.service.list_course_versions(
        actor_id=ALPHA_AUTHOR_ID,
        tenant_id=ALPHA_TENANT_ID,
        course_id=published.course.id,
        cursor=None,
        limit=50,
    )
    assert [item.version_number for item in history.versions] == [2, 1]
    assert history.current_published_version_id == published.version.id


def test_service_principal_fixture_is_really_nonhuman() -> None:
    assert (
        CourseServiceHarness()
        .authorization.actor_for(ALPHA_SERVICE_ID, ALPHA_TENANT_ID)
        .principal_type
        is PrincipalType.SERVICE
    )
