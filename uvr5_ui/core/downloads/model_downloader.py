"""Manual model downloads, for when audio-separator's automatic download fails."""

import logging
import os
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Iterator

from uvr5_ui import paths
from uvr5_ui.core.models.catalog import Model

logger = logging.getLogger(__name__)

ProgressFn = Callable[[float, str], None]

METHOD_PYTHON = "Python (built-in)"
METHODS = [METHOD_PYTHON, "wget", "curl"]
# UI label -> catalog source key
SOURCES = {"Github": "github", "Hugging Face": "huggingface"}

_CHUNK = 1024 * 1024


def _noop_progress(fraction: float, desc: str) -> None:
    pass


def filename_from_url(url: str) -> str:
    return os.path.basename(urllib.parse.urlparse(url).path)


def _download_python(url: str, dest: Path, on_fraction: Callable[[float], None]) -> None:
    tmp = dest.with_name(dest.name + ".part")
    try:
        with urllib.request.urlopen(url) as response, open(tmp, "wb") as f:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            while chunk := response.read(_CHUNK):
                f.write(chunk)
                done += len(chunk)
                if total:
                    on_fraction(done / total)
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)


def _download_external(method: str, url: str, dest: Path, on_fraction: Callable[[float], None]) -> None:
    if method == "wget":
        cmd = ["wget", "--progress=bar:force", "-O", str(dest), url]
    else:
        cmd = ["curl", "-L", "-#", "-o", str(dest), url]

    process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                               universal_newlines=True, bufsize=1)
    for line in process.stderr:
        try:
            if method == "wget" and "%" in line:
                on_fraction(int(line.strip().split("%")[0].split()[-1]) / 100)
            elif method == "curl" and "#" in line:
                on_fraction(min(line.count("#") / 50, 1.0))
        except (ValueError, IndexError):
            pass
    if process.wait() != 0:
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"{method} exited with code {process.returncode}")


def download_model(
    model: Model,
    source: str,
    method: str,
    *,
    models_dir: Path = None,
    progress: ProgressFn = _noop_progress,
) -> Iterator[str]:
    """Download every file of ``model`` (weights + config). Yields one log line at a time."""
    if method not in METHODS:
        yield f"Unsupported download method: {method}"
        return
    urls = model.urls(SOURCES.get(source, source or "github"))
    if not urls:
        yield f"No URLs found for model '{model.id}' using source '{source}'."
        return

    models_dir = Path(models_dir or paths.MODELS_DIR)
    models_dir.mkdir(parents=True, exist_ok=True)
    total = len(urls)
    progress(0, "Starting downloads...")

    for i, url in enumerate(urls):
        filename = filename_from_url(url)
        dest = models_dir / filename
        if dest.exists():
            yield f"{filename} already exists."
            continue

        def on_fraction(fraction, i=i, filename=filename):
            progress((i + fraction) / total, f"File {i + 1}/{total}: {filename} ({int(fraction * 100)}%)")

        progress(i / total, f"Starting download of {filename} ({i + 1}/{total})")
        yield f"Downloading {filename} from {urllib.parse.urlparse(url).netloc}..."
        try:
            if method == METHOD_PYTHON:
                _download_python(url, dest, on_fraction)
            else:
                _download_external(method, url, dest, on_fraction)
            yield f"{filename} downloaded successfully!"
        except FileNotFoundError:
            yield f"Error downloading {filename}: '{method}' is not installed"
        except Exception as e:
            logger.exception("Download of %s failed", url)
            yield f"Error downloading {filename}: {e}"

    progress(1.0, "Download process completed")
