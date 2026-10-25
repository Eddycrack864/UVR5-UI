"""Make the Hugging Face Space a copy of the repository at a given commit or tag.

The Space gets every tracked file of ``--ref`` except two, which are generated:

- README.md: the Space configuration (YAML header) followed by the repository's README.
- requirements.txt: the repository's, plus torch. The installers install torch on their own, and
  ZeroGPU needs torch 2.8 or newer on Python 3.12, while the installers use Python 3.13.

The Space keeps its own .gitattributes, and its files that are not in the repository are deleted.
The app adapts itself to the Space (see uvr5_ui/hosting.py).

    python tools/sync_space.py                       # dry run: show what would change
    python tools/sync_space.py --ref v2.0.0 --upload # upload (needs `hf auth login` with write access)
"""

import argparse
import io
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SPACE_ID = "Eddycrack864/UVR5-UI"
# ZeroGPU supports Python 3.12 and torch 2.8+ (https://huggingface.co/docs/hub/spaces-zerogpu).
# torch 2.9 wheels on PyPI use CUDA 12.8, like onnxruntime-gpu<1.27 (see requirements.txt).
PYTHON_VERSION = "3.12.12"
TORCH_VERSION = "2.9.1"
TORCHVISION_VERSION = "0.24.1"
KEEP_ON_SPACE = {".gitattributes"}
GENERATED = {"README.md", "requirements.txt"}

SPACE_HEADER = """---
title: UVR5 UI
emoji: 🚀
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: {gradio_version}
python_version: "{python_version}"
app_file: app.py
suggested_hardware: zero-a10g
pinned: true
license: mit
short_description: Separate audio into stems with the models of UVR5
---

"""


def export(ref: str, dest: Path) -> list[str]:
    """Write the tracked files of ``ref`` into ``dest``; returns their paths."""
    archive = subprocess.run(["git", "archive", "--format=tar", ref], cwd=REPO_ROOT, check=True,
                             capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        members = [m for m in tar.getmembers() if m.isfile()]
        tar.extractall(dest, members=members, filter="data")
    return sorted(m.name for m in members)


def gradio_version(requirements: str) -> str:
    match = re.search(r"^gradio==([\w.]+)", requirements, re.MULTILINE)
    if not match:
        raise SystemExit("requirements.txt must pin gradio (gradio==X.Y.Z): the Space uses the same version")
    return match.group(1)


def build(ref: str, dest: Path) -> list[str]:
    """Write the Space's files into ``dest``; returns their paths."""
    files = export(ref, dest)
    requirements = (dest / "requirements.txt").read_text(encoding="utf-8")
    header = SPACE_HEADER.format(gradio_version=gradio_version(requirements), python_version=PYTHON_VERSION)
    readme = dest / "README.md"
    readme.write_text(header + readme.read_text(encoding="utf-8"), encoding="utf-8")
    (dest / "requirements.txt").write_text(
        requirements.rstrip("\n")
        + f"\n# Added for the Hugging Face Space (tools/sync_space.py)\n"
        f"torch=={TORCH_VERSION}\ntorchvision=={TORCHVISION_VERSION}\n",
        encoding="utf-8",
    )
    for name in KEEP_ON_SPACE:
        (dest / name).unlink(missing_ok=True)
    return [f for f in files if f not in KEEP_ON_SPACE]


def stale_files(space_files: list[str], files: list[str]) -> list[str]:
    """Files of the Space that are not in the repository any more."""
    return sorted(set(space_files) - set(files) - KEEP_ON_SPACE)


def _escape(path: str) -> str:
    # upload_folder takes glob patterns: match each path literally
    return re.sub(r"([*?\[])", r"[\1]", path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ref", default="HEAD", help="commit, branch or tag to copy (default: HEAD)")
    parser.add_argument("--space", default=SPACE_ID, help=f"Space to update (default: {SPACE_ID})")
    parser.add_argument("--upload", action="store_true", help="upload to the Space (default: dry run)")
    args = parser.parse_args(argv)

    from huggingface_hub import HfApi

    api = HfApi()
    commit = subprocess.run(["git", "rev-parse", "--short", args.ref], cwd=REPO_ROOT, check=True,
                            capture_output=True, text=True).stdout.strip()
    with tempfile.TemporaryDirectory() as tmp:
        bundle = Path(tmp)
        files = build(args.ref, bundle)
        stale = stale_files(api.list_repo_files(args.space, repo_type="space"), files)

        print(f"{args.space} <- {args.ref} ({commit}): {len(files)} files")
        print(f"Generated: {', '.join(sorted(GENERATED))}")
        print(f"To delete ({len(stale)}):" + "".join(f"\n    {name}" for name in stale))
        if not args.upload:
            print("\nDry run. Run again with --upload to update the Space.")
            return 0

        info = api.upload_folder(
            repo_id=args.space, repo_type="space", folder_path=bundle,
            commit_message=f"Sync with UVR5 UI {args.ref} ({commit})",
            delete_patterns=[_escape(name) for name in stale] or None,
        )
        print(f"Uploaded: {info.commit_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
