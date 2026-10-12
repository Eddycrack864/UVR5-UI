"""One-off migration of assets/models.json to the v2 catalog schema.

Reads the model lists hardcoded in the legacy app.py (which define the dropdown
order) and merges them with the download URLs from the v1 models.json.

    python tools/migrate_models_json.py [--app app.py] [--models assets/models.json]
"""

import argparse
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# legacy variable in app.py -> arch id
LEGACY_LISTS = {
    "roformer_models": "roformer",
    "mdx23c_models": "mdx23c",
    "mdxnet_models": "mdxnet",
    "vrarch_models": "vrarch",
    "demucs_models": "demucs",
}
SOURCE_KEYS = {"Github": "github", "HuggingFace": "huggingface"}


def read_legacy_lists(app_path: Path) -> dict:
    tree = ast.parse(app_path.read_text(encoding="utf-8"))
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in LEGACY_LISTS:
                found[name] = ast.literal_eval(node.value)
    missing = set(LEGACY_LISTS) - set(found)
    if missing:
        raise SystemExit(f"Legacy lists not found in {app_path}: {sorted(missing)}")
    return found


def migrate(app_path: Path, models_path: Path) -> dict:
    legacy = read_legacy_lists(app_path)
    v1 = json.loads(models_path.read_text(encoding="utf-8"))
    if isinstance(v1, dict) and v1.get("version") == 2:
        raise SystemExit(f"{models_path} is already v2")

    models = []
    for var, arch in LEGACY_LISTS.items():
        entries = legacy[var]
        pairs = entries.items() if isinstance(entries, dict) else ((f, f) for f in entries)
        for model_id, filename in pairs:
            urls = v1.get(model_id, {})
            sources = {SOURCE_KEYS[k]: v for k, v in urls.items() if k in SOURCE_KEYS and v}
            models.append({"id": model_id, "arch": arch, "filename": filename, "sources": sources})

    unused = set(v1) - {m["id"] for m in models}
    if unused:
        print(f"Warning: entries in {models_path} not referenced by app.py: {sorted(unused)}")
    return {"version": 2, "models": models}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--app", type=Path, default=ROOT / "app.py")
    parser.add_argument("--models", type=Path, default=ROOT / "assets" / "models.json")
    args = parser.parse_args()

    catalog = migrate(args.app, args.models)
    with open(args.models, "w", encoding="utf-8", newline="\n") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
        f.write("\n")

    counts = {}
    for m in catalog["models"]:
        counts[m["arch"]] = counts.get(m["arch"], 0) + 1
    print(f"Wrote {len(catalog['models'])} models to {args.models}: {counts}")


if __name__ == "__main__":
    main()
