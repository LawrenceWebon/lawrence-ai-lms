from __future__ import annotations

from uuid import UUID

import pytest

from lms.modules.learning.errors import LearningError
from lms.modules.learning.policies import (
    PERMISSION_ENROLLMENTS_MANAGE,
    PERMISSION_PLAYBACK_READ,
    require_learner_relationship,
    require_permission,
)
from lms.modules.learning.types import AuthorizedActor

TENANT_ID = UUID("00000000-0000-4000-8000-0000000000a1")
ACTOR_ID = UUID("00000000-0000-4000-8000-000000000101")
LEARNER_MEMBERSHIP_ID = UUID("00000000-0000-4000-8000-000000000302")
OTHER_MEMBERSHIP_ID = UUID("00000000-0000-4000-8000-000000000303")


def actor(*permissions: str) -> AuthorizedActor:
    return AuthorizedActor(
        principal_id=ACTOR_ID,
        tenant_id=TENANT_ID,
        membership_id=LEARNER_MEMBERSHIP_ID,
        permissions=frozenset(permissions),
    )


def test_permissions_are_independent_and_least_privilege() -> None:
    learner = actor(PERMISSION_PLAYBACK_READ)
    administrator = actor(PERMISSION_ENROLLMENTS_MANAGE)

    require_permission(learner, PERMISSION_PLAYBACK_READ)
    require_permission(administrator, PERMISSION_ENROLLMENTS_MANAGE)

    with pytest.raises(LearningError, match="LEARNING_RESOURCE_NOT_FOUND"):
        require_permission(learner, PERMISSION_ENROLLMENTS_MANAGE)
    with pytest.raises(LearningError, match="LEARNING_RESOURCE_NOT_FOUND"):
        require_permission(administrator, PERMISSION_PLAYBACK_READ)


def test_playback_requires_the_current_learners_own_enrollment() -> None:
    learner = actor(PERMISSION_PLAYBACK_READ)

    require_learner_relationship(learner, LEARNER_MEMBERSHIP_ID)

    with pytest.raises(LearningError, match="LEARNING_RESOURCE_NOT_FOUND"):
        require_learner_relationship(learner, OTHER_MEMBERSHIP_ID)
