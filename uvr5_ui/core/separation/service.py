"""Separation use cases, independent of the UI framework."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from uvr5_ui import paths
from uvr5_ui.core.audio import list_audio_files, parse_stem_label, rename_output
from uvr5_ui.core.errors import SeparationError
from uvr5_ui.core.models.catalog import Model
from uvr5_ui.core.separation.runtime import RuntimeOptions, SeparatorCache, execution_summary, separator_cache
from uvr5_ui.core.separation.specs import ArchSpec

logger = logging.getLogger(__name__)

ProgressFn = Callable[[float, str], None]


def noop_progress(fraction: float, desc: str) -> None:
    pass


def describe_error(e: Exception) -> str:
    # Matched by name: importing audio_separator's exceptions would import torch
    kind = type(e).__name__
    if kind == "AudioExportError":
        return f"could not write the output file ({e}). Check the output format and that FFmpeg is installed"
    if kind == "InvalidAudioDataError":
        return f"the audio is empty or invalid ({e})"
    # Some errors carry no message (e.g. audioread's NoBackendError for unreadable files)
    return str(e) or kind


def resolve_batch_dirs(input_dir: str, output_dir: str) -> tuple[Path, Path]:
    """Validate a batch input folder and create the output folder (``outputs/`` when empty)."""
    input_dir = Path(input_dir.strip()) if input_dir and input_dir.strip() else None
    if input_dir is None or not input_dir.is_dir():
        raise SeparationError(f"Input path is not a folder: {input_dir}")
    output_dir = Path(output_dir.strip()) if output_dir and output_dir.strip() else paths.OUTPUTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    return input_dir, output_dir


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
    progress: ProgressFn = noop_progress,
    cache: SeparatorCache = separator_cache,
    options: RuntimeOptions = None,
) -> list[StemResult]:
    if not audio_path:
        raise SeparationError("No input audio")
    output_dir = Path(output_dir or paths.OUTPUTS_DIR)

    try:
        progress(0.2, "Loading model...")
        separator = cache.get(spec, model, values, output_dir, output_format, options=options)
        summary = execution_summary(separator)
        progress(0.7, f"Separating audio ({summary})..." if summary else "Separating audio...")
        outputs = separator.separate(audio_path)
    except Exception as e:
        cache.clear()
        raise SeparationError(f"{spec.tab_label} separation failed: {describe_error(e)}") from e
    if not outputs:
        # audio-separator raises on a failed file (older versions returned []); keep the guard just in case
        raise SeparationError(f"{spec.tab_label} separation produced no output, check the console for details")

    template = (options or RuntimeOptions()).name_template
    return [
        StemResult(str(rename_output(Path(output_dir, name), template)), parse_stem_label(name))
        for name in outputs
    ]


def separate_batch(
    spec: ArchSpec,
    model: Model,
    input_dir: str,
    output_dir: str,
    output_format: str,
    values: dict,
    *,
    progress: ProgressFn = noop_progress,
    cache: SeparatorCache = separator_cache,
    options: RuntimeOptions = None,
) -> Iterator[str]:
    """Separate every audio file in ``input_dir``. Yields one log line at a time.

    A failing file is reported and skipped; the rest of the batch keeps going.
    """
    input_dir, output_dir = resolve_batch_dirs(input_dir, output_dir)
    files = list_audio_files(input_dir)
    if not files:
        yield "No valid audio files."
        return

    total = len(files)
    yield f"{total} audio files found"
    progress(0, "Starting processing...")

    try:
        yield "Loading model..."
        separator = cache.get(spec, model, values, output_dir, output_format, options=options)
    except Exception as e:
        cache.clear()
        raise SeparationError(f"Could not load model {model.id}: {describe_error(e)}") from e
    if summary := execution_summary(separator):
        yield f"Model loaded ({summary})"

    failed = []
    for i, file in enumerate(files):
        progress(i / total, f"Processing file {i + 1}/{total}")
        yield f"Separating file: {file.name}"
        try:
            outputs = separator.separate(str(file))
            if not outputs:
                raise SeparationError("no output produced, check the console for details")
            for name in outputs:
                rename_output(Path(output_dir, name), (options or RuntimeOptions()).name_template)
            yield f"File: {file.name} separated!"
        except Exception as e:
            logger.warning("Batch separation failed for %s: %s", file, describe_error(e))
            failed.append(file.name)
            yield f"Error separating {file.name}: {describe_error(e)}"

    progress(1.0, "Processing complete")
    yield f"Done: {total - len(failed)} separated, {len(failed)} failed. Output: {output_dir}"
