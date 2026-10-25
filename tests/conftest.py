import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def pytest_addoption(parser):
    parser.addoption("--network", action="store_true", help="also run the tests that need internet access")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--network"):
        return
    skip = pytest.mark.skip(reason="needs internet access: run pytest with --network")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def english_ui():
    """UI strings in English, whatever language is selected in the developer's own user_data."""
    from uvr5_ui.i18n import I18nAuto, i18n

    i18n.reset(I18nAuto(language="en_US"))
    yield
    i18n.reset()


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
