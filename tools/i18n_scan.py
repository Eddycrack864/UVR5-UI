"""Find translatable strings in uvr5_ui/ and compare them with the language files.

Strings are collected from literal calls to ``i18n("...")`` and ``N_("...")``.

    python tools/i18n_scan.py            # report (same as --check, but always exits 0)
    python tools/i18n_scan.py --check    # exit 1 if en_US.json is missing keys used in code
    python tools/i18n_scan.py --write    # rewrite en_US.json with exactly the keys used in code
    python tools/i18n_scan.py --langs    # also list missing keys for every other language
    python tools/i18n_scan.py --check --langs  # exit 1 if any language is missing keys
"""

import argparse
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "uvr5_ui"
LANG_DIR = ROOT / "assets" / "i18n" / "languages"
REFERENCE = LANG_DIR / "en_US.json"
MARKERS = {"i18n", "N_"}


def extract_keys(tree: ast.AST) -> set[str]:
    keys = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in MARKERS
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            keys.add(node.args[0].value)
    return keys


def scan(source_dir: Path = SOURCE_DIR) -> set[str]:
    keys = set()
    for path in sorted(source_dir.rglob("*.py")):
        keys |= extract_keys(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
    return keys


def load_language(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="exit with status 1 if en_US.json is missing keys")
    mode.add_argument("--write", action="store_true", help="rewrite en_US.json from the keys found in code")
    parser.add_argument("--langs", action="store_true", help="report missing keys for every language")
    args = parser.parse_args(argv)

    code_keys = scan()
    reference = load_language(REFERENCE)
    missing = sorted(code_keys - set(reference))
    unused = sorted(set(reference) - code_keys)

    print(f"Keys used in code: {len(code_keys)}")
    print(f"Missing from {REFERENCE.name}: {len(missing)}")
    for key in missing:
        print(f"\t{key}")
    print(f"Unused in {REFERENCE.name}: {len(unused)}")
    for key in unused:
        print(f"\t{key}")

    incomplete = []
    if args.langs:
        for path in sorted(LANG_DIR.glob("*.json")):
            if path == REFERENCE:
                continue
            lang_missing = sorted(code_keys - set(load_language(path)))
            print(f"{path.stem}: {len(lang_missing)} missing (falls back to English)")
            for key in lang_missing:
                print(f"\t{key}")
            if lang_missing:
                incomplete.append(path.stem)

    if args.write:
        with open(REFERENCE, "w", encoding="utf-8", newline="\n") as f:
            json.dump({key: key for key in sorted(code_keys)}, f, ensure_ascii=False, indent=4)
            f.write("\n")
        print(f"Wrote {len(code_keys)} keys to {REFERENCE}")
        return 0

    return 1 if args.check and (missing or incomplete) else 0


if __name__ == "__main__":
    sys.exit(main())
