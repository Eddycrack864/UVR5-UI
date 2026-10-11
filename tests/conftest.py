import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def tmp_root(tmp_path):
    """A throwaway app root with a copy of the bundled assets (no user data)."""
    shutil.copytree(
        REPO_ROOT / "assets",
        tmp_path / "assets",
        ignore=shutil.ignore_patterns("*.py", "__pycache__", "config.json", "custom_settings.json"),
    )
    for name in ("models", "outputs", "ytdl"):
        (tmp_path / name).mkdir()
    return tmp_path
