from __future__ import annotations

import stat
import uuid
from pathlib import Path

import pytest

from lms.modules.documents.storage import LocalQuarantineStorage


def test_local_quarantine_uses_private_permissions_and_opaque_locator(tmp_path: Path) -> None:
    root = tmp_path / "private-quarantine"
    storage = LocalQuarantineStorage(root)
    intent_id = uuid.uuid4()
    body = b"%PDF-1.4\nsynthetic private bytes\n%%EOF\n"

    observation = storage.put(intent_id=intent_id, body=body)
    object_path = root / observation.locator

    assert observation.locator == f"{intent_id.hex}.pdf"
    assert "/" not in observation.locator
    assert storage.read(observation.locator) == body
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert stat.S_IMODE(object_path.stat().st_mode) == 0o600
    storage.delete(observation.locator)
    assert not storage.exists(observation.locator)


@pytest.mark.parametrize(
    "locator",
    ("../outside.pdf", "/absolute.pdf", "tenant/source.pdf", "not-an-object-key"),
)
def test_local_quarantine_rejects_path_traversal_and_caller_selected_paths(
    tmp_path: Path, locator: str
) -> None:
    storage = LocalQuarantineStorage(tmp_path / "private-quarantine")

    with pytest.raises(ValueError, match="invalid private quarantine locator"):
        storage.read(locator)
    with pytest.raises(ValueError, match="invalid private quarantine locator"):
        storage.delete(locator)
