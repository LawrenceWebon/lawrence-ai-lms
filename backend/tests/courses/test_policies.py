from __future__ import annotations

from dataclasses import replace

import pytest

from lms.modules.courses.errors import CourseLifecycleError
from lms.modules.courses.policies import (
    DEFAULT_ROLE_PERMISSIONS,
    PERMISSION_COURSES_DRAFTS_WRITE,
    PERMISSION_COURSES_PUBLISH,
    PERMISSION_COURSES_READ,
    PERMISSION_COURSES_REVIEW,
    authorize_transition,
    require_mutable_version,
    require_permission,
)
from lms.modules.courses.types import (
    CourseStatus,
    PrincipalType,
    ReviewerPolicy,
    Transition,
)
from tests.contract_fakes.f002_courses import actor, aggregate_from_contract


def test_default_role_permission_matrix_is_exact() -> None:
    assert DEFAULT_ROLE_PERMISSIONS == {
        "tenant_admin": frozenset(
            {
                PERMISSION_COURSES_READ,
                PERMISSION_COURSES_DRAFTS_WRITE,
                PERMISSION_COURSES_REVIEW,
                PERMISSION_COURSES_PUBLISH,
            }
        ),
        "instructor": frozenset(
            {
                PERMISSION_COURSES_READ,
                PERMISSION_COURSES_DRAFTS_WRITE,
                PERMISSION_COURSES_REVIEW,
                PERMISSION_COURSES_PUBLISH,
            }
        ),
        "reviewer": frozenset({PERMISSION_COURSES_READ, PERMISSION_COURSES_REVIEW}),
        "learner": frozenset(),
    }


def test_explicit_permission_removal_fails_closed() -> None:
    principal = actor(permissions=frozenset({PERMISSION_COURSES_READ}))
    require_permission(principal, PERMISSION_COURSES_READ)

    with pytest.raises(CourseLifecycleError, match="COURSE_PERMISSION_DENIED"):
        require_permission(principal, PERMISSION_COURSES_DRAFTS_WRITE)


@pytest.mark.parametrize(
    ("status", "transition", "target"),
    [
        ("draft", Transition.SUBMIT_REVIEW, "under_review"),
        ("changes_requested", Transition.SUBMIT_REVIEW, "under_review"),
        ("under_review", Transition.REQUEST_CHANGES, "changes_requested"),
        ("under_review", Transition.APPROVE, "approved"),
        ("approved", Transition.PUBLISH, "published"),
        ("published", Transition.WITHDRAW, "withdrawn"),
        ("withdrawn", Transition.ARCHIVE, "archived"),
    ],
)
def test_every_allowed_transition_is_explicit(
    status: str, transition: Transition, target: str
) -> None:
    aggregate = aggregate_from_contract(
        status=status,
        submitted_by_actor_id=actor().principal_id,
    )
    decision = authorize_transition(actor(), aggregate, transition)

    assert decision.target_status == target


_ALLOWED_PAIRS = {
    (CourseStatus.DRAFT, Transition.SUBMIT_REVIEW),
    (CourseStatus.CHANGES_REQUESTED, Transition.SUBMIT_REVIEW),
    (CourseStatus.UNDER_REVIEW, Transition.REQUEST_CHANGES),
    (CourseStatus.UNDER_REVIEW, Transition.APPROVE),
    (CourseStatus.APPROVED, Transition.PUBLISH),
    (CourseStatus.PUBLISHED, Transition.WITHDRAW),
    (CourseStatus.WITHDRAWN, Transition.ARCHIVE),
}


@pytest.mark.parametrize(
    ("status", "transition"),
    [
        (status, transition)
        for status in CourseStatus
        for transition in Transition
        if (status, transition) not in _ALLOWED_PAIRS
    ],
)
def test_forbidden_transition_state_pairs_fail_deterministically(
    status: CourseStatus, transition: Transition
) -> None:
    aggregate = aggregate_from_contract(status=status)

    with pytest.raises(CourseLifecycleError) as caught:
        authorize_transition(actor(), aggregate, transition)
    assert caught.value.code in {"COURSE_VERSION_IMMUTABLE", "VERSION_CONFLICT"}


@pytest.mark.parametrize(
    "principal_type",
    [
        PrincipalType.AI,
        PrincipalType.WORKER,
        PrincipalType.SERVICE,
        PrincipalType.PROVIDER,
        PrincipalType.PRIVILEGED_OPERATOR,
    ],
)
@pytest.mark.parametrize(
    "transition",
    [
        Transition.REQUEST_CHANGES,
        Transition.APPROVE,
        Transition.PUBLISH,
        Transition.WITHDRAW,
        Transition.ARCHIVE,
    ],
)
def test_nonhuman_principals_cannot_review_approve_or_publish(
    principal_type: PrincipalType, transition: Transition
) -> None:
    source = {
        Transition.REQUEST_CHANGES: "under_review",
        Transition.APPROVE: "under_review",
        Transition.PUBLISH: "approved",
        Transition.WITHDRAW: "published",
        Transition.ARCHIVE: "withdrawn",
    }[transition]
    aggregate = aggregate_from_contract(status=source, submitted_by_actor_id=actor().principal_id)

    with pytest.raises(CourseLifecycleError, match="HUMAN_ACTION_REQUIRED"):
        authorize_transition(actor(principal_type=principal_type), aggregate, transition)


def test_reviewer_policy_allows_audited_self_review_or_requires_separation() -> None:
    principal = actor()
    aggregate = aggregate_from_contract(
        status="under_review",
        submitted_by_actor_id=principal.principal_id,
    )

    assert authorize_transition(principal, aggregate, Transition.APPROVE).self_review is True

    separate = replace(
        aggregate,
        course=replace(aggregate.course, reviewer_policy=ReviewerPolicy.SEPARATE_REVIEWER_REQUIRED),
    )
    with pytest.raises(CourseLifecycleError, match="REVIEWER_SEPARATION_REQUIRED"):
        authorize_transition(principal, separate, Transition.APPROVE)

    assert (
        authorize_transition(actor(reviewer=True), separate, Transition.APPROVE).self_review
        is False
    )


@pytest.mark.parametrize("status", ["draft", "changes_requested"])
def test_only_declared_mutable_states_allow_content_changes(status: str) -> None:
    require_mutable_version(aggregate_from_contract(status=status).version)


@pytest.mark.parametrize(
    "status", ["under_review", "approved", "scheduled", "published", "withdrawn", "archived"]
)
def test_all_other_states_are_immutable(status: str) -> None:
    with pytest.raises(CourseLifecycleError, match="COURSE_VERSION_IMMUTABLE"):
        require_mutable_version(aggregate_from_contract(status=status).version)
