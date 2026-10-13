"""Check that the download links of assets/models.json work.

Every URL is requested (only its first byte), so a link counts as working only if the
file can actually be downloaded. For models that have no Hugging Face source it also
checks the path they would have on the mirror, to tell whether they were uploaded yet.

    python tools/check_model_links.py                        # every model, both sources
    python tools/check_model_links.py --source huggingface   # only one source
    python tools/check_model_links.py --arch roformer --verbose
    python tools/check_model_links.py --json links.json      # also save the full report

Exit status 1 if a link in the catalog is broken.
"""

import argparse
import json
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "assets" / "models.json"
SOURCES = ("github", "huggingface")

GITHUB_MODEL_CONFIGS = "https://github.com/nomadkaraoke/python-audio-separator/releases/download/model-configs"
UVR_MODEL_REPO = "https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models"
HF_MIRROR = "https://huggingface.co/Eddycrack864/audio-separator-models/resolve/main"
HF_FOLDERS = {"roformer": "roformers", "mdx23c": "mdx23c", "mdxnet": "mdx-net", "vrarch": "vr-arch"}

USER_AGENT = "UVR5-UI model link checker"


@dataclass(frozen=True)
class LinkResult:
    url: str
    ok: bool
    status: int | None = None
    error: str = ""


Checker = Callable[[str], LinkResult]


def check_url(url: str, timeout: float = 30, retries: int = 3) -> LinkResult:
    """Download the first byte of ``url`` (following redirects)."""
    request = Request(url, headers={"Range": "bytes=0-0", "User-Agent": USER_AGENT})
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                return LinkResult(url, response.status in (200, 206), response.status)
        except HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(2 ** attempt * 2)  # rate limited or flaky: back off and retry
                continue
            return LinkResult(url, False, e.code, str(e.reason))
        except (URLError, TimeoutError, OSError) as e:
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            return LinkResult(url, False, None, str(getattr(e, "reason", e)))
    raise AssertionError("unreachable")


def check_urls(urls: Iterable[str], checker: Checker = check_url, workers: int = 8) -> dict[str, LinkResult]:
    unique = list(dict.fromkeys(urls))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return dict(zip(unique, pool.map(checker, unique)))


def file_name(url: str) -> str:
    return Path(urllib.parse.urlparse(url).path).name


def model_files(model: dict) -> list[str]:
    """Files a model needs (weights + config), taken from its download URLs."""
    for source in SOURCES:
        urls = model.get("sources", {}).get(source) or []
        if urls:
            return [file_name(u) for u in urls]
    return []


def huggingface_urls(model: dict, files: list[str] | None = None) -> list[str]:
    """Where the model's files live (or would live) on the Hugging Face mirror."""
    folder = HF_FOLDERS.get(model["arch"])
    files = model_files(model) if files is None else files
    if folder is None or not files:
        return []
    return [f"{HF_MIRROR}/{folder}/{urllib.parse.quote(name)}" for name in files]


def load_catalog(path: Path = CATALOG) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["models"]


def build_report(models: list[dict], sources=SOURCES, checker: Checker = check_url, workers: int = 8) -> list[dict]:
    """One entry per model: the result of each of its sources, plus the expected mirror path when it has none."""
    wanted = []
    for model in models:
        for source in sources:
            wanted += model.get("sources", {}).get(source) or []
        if "huggingface" in sources and not model.get("sources", {}).get("huggingface"):
            wanted += huggingface_urls(model)
    results = check_urls(wanted, checker, workers)

    report = []
    for model in models:
        entry = {"id": model["id"], "arch": model["arch"], "filename": model["filename"], "sources": {}}
        for source in sources:
            urls = model.get("sources", {}).get(source) or []
            entry["sources"][source] = [asdict(results[u]) for u in urls]
        if "huggingface" in sources and not model.get("sources", {}).get("huggingface"):
            expected = huggingface_urls(model)
            entry["huggingface_expected"] = [asdict(results[u]) for u in expected]
        report.append(entry)
    return report


def summarize(entry: dict) -> dict[str, str]:
    """Per source: ok, broken, none (no URLs), plus "mirror" for models without a Hugging Face source."""
    status = {}
    for source, links in entry["sources"].items():
        status[source] = "none" if not links else ("ok" if all(link["ok"] for link in links) else "broken")
    if "huggingface_expected" in entry:
        expected = entry["huggingface_expected"]
        if not expected:
            status["mirror"] = "n/a"
        else:
            status["mirror"] = "uploaded" if all(link["ok"] for link in expected) else "not uploaded"
    return status


def _describe(link: dict) -> str:
    return f"{link['status'] or ''} {link['error']}".strip() or "ok"


def print_report(report: list[dict], verbose: bool = False) -> int:
    broken = 0
    counts: dict[tuple[str, str], int] = {}
    for entry in report:
        status = summarize(entry)
        for key, value in status.items():
            counts[(key, value)] = counts.get((key, value), 0) + 1
        problems = [k for k, v in status.items() if v in ("broken", "not uploaded", "uploaded")]
        if not verbose and not problems:
            continue
        print(f"[{entry['arch']}] {entry['id']}")
        for source, links in entry["sources"].items():
            for link in links:
                if verbose or not link["ok"]:
                    print(f"    {source:<12} {'OK ' if link['ok'] else 'BROKEN'} {_describe(link):<20} {link['url']}")
            broken += sum(not link["ok"] for link in links)
        for link in entry.get("huggingface_expected", []):
            state = "on the mirror  " if link["ok"] else "NOT on the mirror"
            print(f"    {'mirror':<12} {state} {link['url']}")
        if status.get("mirror") == "uploaded":
            print(f"    {'mirror':<12} every file is uploaded: run tools/sync_models.py --write to add the source")

    print("\nSummary")
    for (key, value), count in sorted(counts.items()):
        print(f"    {key:<12} {value:<13} {count}")
    print(f"\n{broken} broken link(s) in the catalog")
    return broken


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", choices=SOURCES, action="append", help="only check this source (repeatable)")
    parser.add_argument("--arch", action="append", help="only check this architecture (repeatable)")
    parser.add_argument("--workers", type=int, default=8, help="parallel requests (default: 8)")
    parser.add_argument("--json", type=Path, help="write the full report to this file")
    parser.add_argument("--verbose", action="store_true", help="list working links too")
    args = parser.parse_args(argv)

    models = [m for m in load_catalog() if not args.arch or m["arch"] in args.arch]
    report = build_report(models, tuple(args.source or SOURCES), workers=args.workers)
    broken = print_report(report, args.verbose)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Report written to {args.json}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
