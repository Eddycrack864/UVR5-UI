"""Bring assets/models.json in line with the models the installed audio-separator supports.

- Adds the models audio-separator supports that the catalog lacks, right after the
  model that precedes them in audio-separator's list (so families stay together).
- Fills the empty GitHub / Hugging Face sources of existing models once their files
  can be downloaded (e.g. after uploading them to the Hugging Face mirror).

Only links that actually work are written: a model whose files are not on the mirror
yet gets no Hugging Face source (run this again after uploading them).
tools/check_model_links.py lists what is missing.

    python tools/sync_models.py            # dry run: show what would change
    python tools/sync_models.py --write    # update assets/models.json

Needs the app's environment (it asks audio-separator for its model list) and network.
"""

import argparse
import json
import logging
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.check_model_links import (  # noqa: E402
    CATALOG, GITHUB_MODEL_CONFIGS, UVR_MODEL_REPO, Checker, check_url, check_urls, huggingface_urls,
)

ROFORMER_PREFIX = "Roformer Model: "
# audio-separator model type -> catalog arch (MDXC holds both MDX23C and Roformer models)
TYPE_ARCH = {"VR": "vrarch", "MDX": "mdxnet", "Demucs": "demucs"}


def arch_for(model_type: str, name: str) -> str:
    if model_type == "MDXC":
        return "roformer" if name.startswith(ROFORMER_PREFIX) or "roformer" in name.lower() else "mdx23c"
    return TYPE_ARCH[model_type]


def id_for(arch: str, name: str, filename: str) -> str:
    """Roformer models show their friendly name; every other architecture shows the filename."""
    if arch == "roformer":
        return name[len(ROFORMER_PREFIX):] if name.startswith(ROFORMER_PREFIX) else name
    return filename


def supported_models(model_dir: Path) -> list[dict]:
    """audio-separator's models in its own order: name, type, filename and the files to download."""
    from audio_separator.separator import Separator

    separator = Separator(info_only=True, log_level=logging.WARNING, model_file_dir=str(model_dir))
    return [
        {"name": name, "type": model_type, "filename": info["filename"], "files": info["download_files"]}
        for model_type, models in separator.list_supported_model_files().items()
        for name, info in models.items()
    ]


def github_candidates(file: str) -> list[str]:
    # The catalog points at audio-separator's mirror first, like the existing entries
    candidates = [f"{GITHUB_MODEL_CONFIGS}/{file}", f"{UVR_MODEL_REPO}/{file}"]
    if file.endswith(".yaml"):
        candidates.append(f"{UVR_MODEL_REPO}/mdx_model_data/mdx_c_configs/{file}")
    return candidates


def working_sources(arch: str, files: list[str], checker: Checker) -> dict:
    """GitHub and Hugging Face URLs for ``files``; a source is left out unless every file downloads."""
    sources = {}
    if not files or any(f.startswith("http") for f in files):  # Demucs weights live outside both
        return sources
    github = []
    for file in files:
        url = next((u for u in github_candidates(file) if checker(u).ok), None)
        if url is None:
            break
        github.append(url)
    if len(github) == len(files):
        sources["github"] = github
    hf = huggingface_urls({"arch": arch}, files)
    if hf and all(checker(u).ok for u in hf):
        sources["huggingface"] = hf
    return sources


def plan(catalog: list[dict], upstream: list[dict], checker: Checker) -> tuple[list[dict], list[str]]:
    """The new catalog and a description of each change."""
    by_file = {m["filename"]: m for m in catalog}
    models = [dict(m) for m in catalog]
    changes = []

    upstream_files = {u["filename"]: u for u in upstream}
    for model in models:  # fill empty sources of existing models
        sources = model.get("sources") or {}
        if all(sources.get(s) for s in ("github", "huggingface")) or model["filename"] not in upstream_files:
            continue
        found = working_sources(model["arch"], upstream_files[model["filename"]]["files"], checker)
        added = {s: urls for s, urls in found.items() if not sources.get(s)}
        if added:
            model["sources"] = {**sources, **added}
            changes.append(f"fill {', '.join(added)} of [{model['arch']}] {model['id']}")

    previous = None
    for item in upstream:
        if item["filename"] in by_file:
            previous = item["filename"]
            continue
        arch = arch_for(item["type"], item["name"])
        entry = {"id": id_for(arch, item["name"], item["filename"]), "arch": arch, "filename": item["filename"],
                 "sources": working_sources(arch, item["files"], checker)}
        index = _insert_index(models, arch, previous)
        models.insert(index, entry)
        by_file[entry["filename"]] = entry
        previous = entry["filename"]
        missing = [s for s in ("github", "huggingface") if s not in entry["sources"]]
        note = f" (no {' / '.join(missing)} source yet)" if missing else ""
        changes.append(f"add [{arch}] {entry['id']}{note}")
    return models, changes


def _insert_index(models: list[dict], arch: str, previous: str | None) -> int:
    """Right after ``previous`` if it has the same arch, else at the end of the arch's group."""
    for i, model in enumerate(models):
        if model["filename"] == previous and model["arch"] == arch:
            return i + 1
    same_arch = [i for i, m in enumerate(models) if m["arch"] == arch]
    return same_arch[-1] + 1 if same_arch else len(models)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true", help="update assets/models.json")
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    args = parser.parse_args(argv)

    data = json.loads(args.catalog.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:  # a fresh copy of UVR's model list, not a cached one
        upstream = supported_models(Path(tmp))

    cache = {}

    def checker(url):
        if url not in cache:
            cache[url] = check_url(url)
        return cache[url]

    # Check up front, in parallel, every link the models that need changes could use
    complete = {m["filename"] for m in data["models"]
                if all((m.get("sources") or {}).get(s) for s in ("github", "huggingface"))}
    wanted = []
    for item in upstream:
        if item["filename"] in complete:
            continue
        files = [f for f in item["files"] if not f.startswith("http")]
        for file in files:
            wanted += github_candidates(file)
        wanted += huggingface_urls({"arch": arch_for(item["type"], item["name"])}, files)
    cache.update(check_urls(wanted))

    models, changes = plan(data["models"], upstream, checker)
    if not changes:
        print("assets/models.json already matches audio-separator")
        return 0
    print("\n".join(changes))
    if args.write:
        data["models"] = models
        args.catalog.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
                                newline="\n")
        print(f"\nWrote {len(models)} models to {args.catalog}")
    else:
        print("\nDry run: use --write to update the catalog")
    return 0


if __name__ == "__main__":
    sys.exit(main())
