"""tools/sync_space.py: the Space is the repository plus a generated README and requirements."""

import shutil

import pytest

from tools import sync_space

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    dest = tmp_path_factory.mktemp("space")
    return dest, sync_space.build("HEAD", dest)


def test_space_has_every_tracked_file_but_gitattributes(bundle):
    dest, files = bundle
    assert {"app.py", "uvr5_ui/main.py", "assets/models.json"} <= set(files)
    assert ".gitattributes" not in files and not (dest / ".gitattributes").exists()
    assert all((dest / name).is_file() for name in files)


def test_readme_starts_with_the_space_configuration(bundle):
    dest, _ = bundle
    readme = (dest / "README.md").read_text(encoding="utf-8")
    header, body = readme.split("\n---\n", 1)
    requirements = (sync_space.REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert header.startswith("---\n")
    assert f"sdk_version: {sync_space.gradio_version(requirements)}" in header
    assert f'python_version: "{sync_space.PYTHON_VERSION}"' in header
    assert "app_file: app.py" in header
    assert "UVR5 UI" in body


def test_requirements_add_torch_for_zerogpu(bundle):
    dest, _ = bundle
    requirements = (dest / "requirements.txt").read_text(encoding="utf-8")
    original = (sync_space.REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert requirements.startswith(original.rstrip("\n"))
    assert f"torch=={sync_space.TORCH_VERSION}" in requirements.splitlines()
    assert int(sync_space.TORCH_VERSION.split(".")[1]) >= 8  # ZeroGPU needs torch 2.8+
    assert "spaces" not in requirements  # the Space provides its own version


def test_stale_files_keep_gitattributes():
    space = [".gitattributes", "README.md", "app.py", "assets/presence/discord_presence.py", "test.mp3"]
    assert sync_space.stale_files(space, ["README.md", "app.py"]) == [
        "assets/presence/discord_presence.py", "test.mp3",
    ]


def test_delete_patterns_match_paths_literally():
    assert sync_space._escape("assets/[old]*.json") == "assets/[[]old][*].json"
