from __future__ import annotations

import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("missing_name", ["DJANGO_SECRET_KEY", "DATABASE_URL"])
def test_production_settings_require_explicit_configuration(missing_name: str) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "DJANGO_SECRET_KEY": "synthetic-test-only-secret",
            "DATABASE_URL": "postgresql://synthetic:synthetic@127.0.0.1:55432/synthetic",
        }
    )
    environment.pop(missing_name)

    result = subprocess.run(
        [sys.executable, "-c", "import lms.config.settings.production"],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    assert result.returncode != 0
    assert missing_name in result.stderr
