"""Separation use cases, independent of the UI framework."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from uvr5_ui import paths
from uvr5_ui.core.audio import list_audio_files, parse_stem_label
from uvr5_ui.core.errors import SeparationError
from uvr5_ui.core.models.catalog import Model
from uvr5_ui.core.separation.runtime import SeparatorCache, separator_cache
from uvr5_ui.core.separation.specs import ArchSpec

logger = logging.getLogger(__name__)

ProgressFn = Callable[[float, str], None]


def _noop_progress(fraction: float, desc: str) -> None:
    pass


@dataclass(frozen=True)
class StemResult:
    path: str
    label: str | None  # e.g. "Vocals", parsed from the output filename


def separate_file(
    spec: ArchSpec,
    model: Model,
    audio_path: str,
    output_format: str,
    values: dict,
    *,
    output_dir: Path = None,
    progress: ProgressFn = _noop_progress,
    cache: SeparatorCache = separator_cache,
) -> list[StemResult]:
    if not audio_path:
        raise SeparationError("No input audio")
    output_dir = Path(output_dir or paths.OUTPUTS_DIR)

    try:
        progress(0.2, "Loading model...")
        separator = cache.get(spec, model, values, output_dir, output_format)
        progress(0.7, "Separating audio...")
        outputs = separator.separate(audio_path)
    except Exception as e:
        cache.clear()
        raise SeparationError(f"{spec.tab_label} separation failed: {e}") from e
    if not outputs:
        # audio-separator logs and swallows per-file errors, returning no outputs
        raise SeparationError(f"{spec.tab_label} separation produced no output, check the console for details")

    return [StemResult(os.path.join(output_dir, name), parse_stem_label(name)) for name in outputs]


def separate_batch(
    spec: ArchSpec,
    model: Model,
    input_dir: str,
    output_dir: str,
    output_format: str,
    values: dict,
    *,
    progress: ProgressFn = _noop_progress,
    cache: SeparatorCache = separator_cache,
) -> Iterator[str]:
    """Separate every audio file in ``input_dir``. Yields one log line at a time.

    A failing file is reported and skipped; the rest of the batch keeps going.
    """
    input_dir = Path(input_dir.strip()) if input_dir and input_dir.strip() else None
    if input_dir is None or not input_dir.is_dir():
        raise SeparationError(f"Input path is not a folder: {input_dir}")
    output_dir = Path(output_dir.strip()) if output_dir and output_dir.strip() else paths.OUTPUTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    files = list_audio_files(input_dir)
    if not files:
        yield "No valid audio files."
        return

    total = len(files)
    yield f"{total} audio files found"
    progress(0, "Starting processing...")

    try:
        yield "Loading model..."
        separator = cache.get(spec, model, values, output_dir, output_format)
    except Exception as e:
        cache.clear()
        raise SeparationError(f"Could not load model {model.id}: {e}") from e

    failed = []
    for i, file in enumerate(files):
        progress(i / total, f"Processing file {i + 1}/{total}")
        yield f"Separating file: {file.name}"
        try:
            if not separator.separate(str(file)):
                raise SeparationError("no output produced, check the console for details")
            yield f"File: {file.name} separated!"
        except Exception as e:
            logger.warning("Batch separation failed for %s: %s", file, e)
            failed.append(file.name)
            yield f"Error separating {file.name}: {e}"

    progress(1.0, "Processing complete")
    yield f"Done: {total - len(failed)} separated, {len(failed)} failed. Output: {output_dir}"
