from __future__ import annotations

from .errors import CourseLifecycleError
from .types import (
    AuthorizedActor,
    CourseAggregate,
    CourseStatus,
    CourseVersion,
    PrincipalType,
    ReviewerPolicy,
    Transition,
    TransitionDecision,
)

PERMISSION_COURSES_READ = "courses.read"
PERMISSION_COURSES_DRAFTS_WRITE = "courses.drafts.write"
PERMISSION_COURSES_REVIEW = "courses.review"
PERMISSION_COURSES_PUBLISH = "courses.publish"

DEFAULT_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
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

_TRANSITIONS: dict[Transition, tuple[frozenset[CourseStatus], CourseStatus, str]] = {
    Transition.SUBMIT_REVIEW: (
        frozenset({CourseStatus.DRAFT, CourseStatus.CHANGES_REQUESTED}),
        CourseStatus.UNDER_REVIEW,
        PERMISSION_COURSES_DRAFTS_WRITE,
    ),
    Transition.REQUEST_CHANGES: (
        frozenset({CourseStatus.UNDER_REVIEW}),
        CourseStatus.CHANGES_REQUESTED,
        PERMISSION_COURSES_REVIEW,
    ),
    Transition.APPROVE: (
        frozenset({CourseStatus.UNDER_REVIEW}),
        CourseStatus.APPROVED,
        PERMISSION_COURSES_REVIEW,
    ),
    Transition.PUBLISH: (
        frozenset({CourseStatus.APPROVED}),
        CourseStatus.PUBLISHED,
        PERMISSION_COURSES_PUBLISH,
    ),
    Transition.WITHDRAW: (
        frozenset({CourseStatus.PUBLISHED}),
        CourseStatus.WITHDRAWN,
        PERMISSION_COURSES_PUBLISH,
    ),
    Transition.ARCHIVE: (
        frozenset({CourseStatus.WITHDRAWN}),
        CourseStatus.ARCHIVED,
        PERMISSION_COURSES_PUBLISH,
    ),
}

_HUMAN_TRANSITIONS = frozenset(
    {
        Transition.REQUEST_CHANGES,
        Transition.APPROVE,
        Transition.PUBLISH,
        Transition.WITHDRAW,
        Transition.ARCHIVE,
    }
)


def require_permission(actor: AuthorizedActor, permission: str) -> None:
    if permission not in actor.permissions:
        raise CourseLifecycleError("COURSE_PERMISSION_DENIED")


def require_mutable_version(version: CourseVersion) -> None:
    if version.status not in {CourseStatus.DRAFT, CourseStatus.CHANGES_REQUESTED}:
        raise CourseLifecycleError("COURSE_VERSION_IMMUTABLE")


def transition_permission(transition: Transition) -> str:
    return _TRANSITIONS[transition][2]


def transition_requires_human(transition: Transition) -> bool:
    return transition in _HUMAN_TRANSITIONS


def require_human(actor: AuthorizedActor) -> None:
    if actor.principal_type is not PrincipalType.USER:
        raise CourseLifecycleError("HUMAN_ACTION_REQUIRED")


def authorize_transition(
    actor: AuthorizedActor,
    aggregate: CourseAggregate,
    transition: Transition,
) -> TransitionDecision:
    allowed_sources, target, permission = _TRANSITIONS[transition]
    require_permission(actor, permission)
    if transition in _HUMAN_TRANSITIONS:
        require_human(actor)
    if aggregate.version.status not in allowed_sources:
        if aggregate.version.status in {
            CourseStatus.APPROVED,
            CourseStatus.SCHEDULED,
            CourseStatus.PUBLISHED,
            CourseStatus.WITHDRAWN,
            CourseStatus.ARCHIVED,
        }:
            raise CourseLifecycleError("COURSE_VERSION_IMMUTABLE")
        raise CourseLifecycleError("VERSION_CONFLICT")

    self_review = False
    if transition in {Transition.REQUEST_CHANGES, Transition.APPROVE}:
        if aggregate.submitted_by_actor_id is None:
            raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")
        self_review = aggregate.submitted_by_actor_id == actor.principal_id
        if (
            self_review
            and aggregate.course.reviewer_policy is ReviewerPolicy.SEPARATE_REVIEWER_REQUIRED
        ):
            raise CourseLifecycleError("REVIEWER_SEPARATION_REQUIRED")

    return TransitionDecision(
        target_status=target,
        required_permission=permission,
        self_review=self_review,
    )
