"""Guards for the distribution scripts."""

import hashlib

from tests.conftest import REPO_ROOT

# cmd.exe keeps reading a running .bat at the same byte offset, and the updater rewrites itself with
# "git reset". Older updaters resume right after the reset block, so the part above the marker must
# stay byte-identical forever.
UPDATER_MARKER = b"rem ===== Do not edit anything above this line. ====="
UPDATER_PREFIX_SHA256 = "5a5368a133c63a95ae257b7fd08504e22d2ca6c262e04fad1fa4f79efef52a51"


def test_windows_updater_prefix_is_unchanged():
    data = (REPO_ROOT / "UVR5-UI-updater.bat").read_bytes()
    prefix, marker, _ = data.partition(UPDATER_MARKER)
    assert marker, "the 'Do not edit' marker is missing from UVR5-UI-updater.bat"
    assert hashlib.sha256(prefix).hexdigest() == UPDATER_PREFIX_SHA256


def test_installers_share_versions():
    bat = (REPO_ROOT / "UVR5-UI-installer.bat").read_text(encoding="utf-8")
    sh = (REPO_ROOT / "UVR5-UI-installer.sh").read_text(encoding="utf-8")
    for name in ("PYTHON_VERSION", "PIP_VERSION", "TORCH_VERSION", "TORCHVISION_VERSION", "TORCH_INDEX"):
        bat_value = next(line for line in bat.splitlines() if line.startswith(f'set "{name}='))
        sh_value = next(line for line in sh.splitlines() if line.startswith(f"{name}="))
        assert bat_value.split("=", 1)[1].rstrip('"') == sh_value.split("=", 1)[1].strip('"'), name
