from __future__ import annotations

from uuid import UUID

from .errors import LearningError
from .types import AuthorizedActor

PERMISSION_ENROLLMENTS_MANAGE = "learning.enrollments.manage"
PERMISSION_PLAYBACK_READ = "learning.playback.read"

DEFAULT_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "tenant_admin": frozenset({PERMISSION_ENROLLMENTS_MANAGE}),
    "instructor": frozenset(),
    "reviewer": frozenset(),
    "learner": frozenset({PERMISSION_PLAYBACK_READ}),
}


def require_permission(actor: AuthorizedActor, permission: str) -> None:
    if permission not in actor.permissions:
        raise LearningError("LEARNING_RESOURCE_NOT_FOUND")


def require_learner_relationship(actor: AuthorizedActor, learner_membership_id: UUID) -> None:
    if actor.membership_id is None or actor.membership_id != learner_membership_id:
        raise LearningError("LEARNING_RESOURCE_NOT_FOUND")
