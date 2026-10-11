from tests.conftest import REPO_ROOT


def test_repo_layout():
    assert (REPO_ROOT / "app.py").is_file()
    assert (REPO_ROOT / "assets" / "default_settings.json").is_file()
