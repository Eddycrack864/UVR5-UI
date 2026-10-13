"""Ensembles: run several models on the same audio and combine their stems.

audio-separator can ensemble by itself (``load_model([...])``), but it reloads every
model for every file, drops the loaded model afterwards and shares a single
``mdxc_params`` between Roformer and MDX23C members. Here each member goes through the
regular ``SeparatorCache`` with the settings of its own architecture, files are
processed model by model (every file of a group with model A, then with model B...)
so each model is loaded once per group, and only the combining step is delegated to
audio-separator's ``Ensembler``.
"""

import logging
import math
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator, Iterator, Sequence

import numpy as np

from uvr5_ui import paths
from uvr5_ui.core.audio import (
    DEFAULT_NAME_TEMPLATE, audio_subtype, list_audio_files, load_audio, normalize_peak, parse_stem_label, render_name,
    write_audio,
)
from uvr5_ui.core.errors import SeparationError
from uvr5_ui.core.models.catalog import Model
from uvr5_ui.core.separation.runtime import (
    RuntimeOptions, SeparatorCache, execution_summary, separation_lock, separator_cache,
)
from uvr5_ui.core.separation.service import (
    ProgressFn, StemResult, describe_error, noop_progress, resolve_batch_dirs,
)
from uvr5_ui.core.separation.specs import ArchSpec
from uvr5_ui.i18n import N_

logger = logging.getLogger(__name__)

# Same names and order as audio-separator's Separator.VALID_ENSEMBLE_ALGORITHMS
ALGORITHMS = (
    "avg_wave", "median_wave", "min_wave", "max_wave",
    "avg_fft", "median_fft", "min_fft", "max_fft",
    "uvr_max_spec", "uvr_min_spec", "ensemble_wav",
)
WEIGHTED_ALGORITHMS = frozenset({"avg_wave", "avg_fft"})  # the others ignore weights
DEFAULT_ALGORITHM = "avg_wave"
MIN_MODELS = 2
MAX_MODELS = 6
DEFAULT_SAMPLE_RATE = 44100
# Files separated by every model before their stems are combined. Bounds the disk used
# by intermediate stems while still loading each model once per group.
GROUP_SIZE = 8
WORK_DIR_NAME = "uvr5_ui-ensemble"

# Canonical stem names used to match stems across models. A superset of audio-separator's
# STEM_NAME_MAP (tests check that they agree).
STEM_NAME_MAP = {
    "vocals": "Vocals",
    "instrumental": "Instrumental",
    "inst": "Instrumental",
    "karaoke": "Instrumental",
    "other": "Other",
    "no_vocals": "Instrumental",
    "no vocals": "Instrumental",
    "drums": "Drums",
    "bass": "Bass",
    "guitar": "Guitar",
    "piano": "Piano",
    "synthesizer": "Synthesizer",
    "strings": "Strings",
    "woodwinds": "Woodwinds",
    "brass": "Brass",
    "wind inst": "Wind Inst",
    "lead vocals": "Lead Vocals",
    "backing vocals": "Backing Vocals",
    "primary stem": "Primary Stem",
    "secondary stem": "Secondary Stem",
}


class EnsembleConfigError(SeparationError):
    """An invalid ensemble setup. ``field`` names the offending input: models, algorithm or weights."""

    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field
        self.message = message  # an i18n key


@dataclass(frozen=True)
class EnsembleMember:
    spec: ArchSpec
    model: Model
    values: dict = field(default_factory=dict, compare=False, hash=False)  # params of its architecture

    def separator_values(self) -> dict:
        # Every member must write all of its stems so they can be matched with the other models
        return {**self.values, "single_stem": ""}


@dataclass(frozen=True)
class EnsembleOptions:
    algorithm: str = DEFAULT_ALGORITHM
    weights: tuple[float, ...] | None = None  # one per member; only used by WEIGHTED_ALGORITHMS
    name: str | None = None  # used in output filenames (e.g. the preset id); defaults to the algorithm
    include_unmatched: bool = False  # also output stems that only some models produce
    keep_intermediates: bool = False  # keep each model's own stems next to the result
    normalization_threshold: float = 0.9
    amplification_threshold: float = 0.0
    sample_rate: int = DEFAULT_SAMPLE_RATE  # the rate audio-separator writes stems at

    @property
    def label(self) -> str:
        return re.sub(r"[^\w.-]+", "_", self.name or self.algorithm).strip("_") or self.algorithm


def check_ensemble(model_count: int, algorithm: str, weights: Sequence[float] | None) -> None:
    """Raise ``EnsembleConfigError`` if the ensemble can't run."""
    if model_count < MIN_MODELS:
        raise EnsembleConfigError("models", N_("Select at least two models for the ensemble"))
    if model_count > MAX_MODELS:
        raise EnsembleConfigError("models", N_("An ensemble can combine at most six models"))
    if algorithm not in ALGORITHMS:
        raise EnsembleConfigError("algorithm", N_("Unknown ensemble algorithm"))
    if weights is None or algorithm not in WEIGHTED_ALGORITHMS:
        return
    if len(weights) != model_count:
        raise EnsembleConfigError("weights", N_("There must be one weight per model"))
    try:
        values = [float(w) for w in weights]
    except (TypeError, ValueError):
        values = [math.nan]
    if not all(math.isfinite(w) and w >= 0 for w in values) or sum(values) <= 0:
        raise EnsembleConfigError("weights", N_("Weights must be non-negative numbers that add up to more than zero"))


def canonical_stem(raw: str, model_stems: Sequence[str]) -> str:
    """Name a model's stem so it matches the same stem of other models ("vocals" == "Vocals")."""
    lower = raw.strip().lower()
    if "vocal" in lower and not lower.startswith("no") and "lead" not in lower and "backing" not in lower:
        return "Vocals"
    if lower == "other" and len(model_stems) == 2 and any("vocal" in s.lower() for s in model_stems):
        # A two-stem vocal model's "other" is the instrumental
        return "Instrumental"
    return STEM_NAME_MAP.get(lower) or raw.strip().title()


def default_work_dir() -> Path:
    # A stable path: a loaded model is cached by its settings, output dir included,
    # so a fresh temp dir per run would reload the model every time.
    return Path(tempfile.gettempdir()) / WORK_DIR_NAME


def ensemble_file(
    members: Sequence[EnsembleMember],
    audio_path: str,
    output_format: str,
    options: EnsembleOptions,
    *,
    output_dir: Path = None,
    progress: ProgressFn = noop_progress,
    cache: SeparatorCache = separator_cache,
    work_dir: Path = None,
    runtime_options: RuntimeOptions = None,
) -> list[StemResult]:
    """Separate ``audio_path`` with every member and combine their stems."""
    check_ensemble(len(members), options.algorithm, options.weights)
    if not audio_path:
        raise SeparationError("No input audio")
    output_dir = Path(output_dir or paths.OUTPUTS_DIR)
    file = Path(audio_path)

    run = _run(members, [file], output_dir, output_format, options, cache, progress, work_dir, runtime_options)
    while True:
        try:
            logger.info(next(run))
        except StopIteration as done:
            outcome = done.value[file]
            break
    if isinstance(outcome, Exception):
        raise SeparationError(f"Ensemble failed: {describe_error(outcome)}") from outcome
    return outcome


def ensemble_batch(
    members: Sequence[EnsembleMember],
    input_dir: str,
    output_dir: str,
    output_format: str,
    options: EnsembleOptions,
    *,
    progress: ProgressFn = noop_progress,
    cache: SeparatorCache = separator_cache,
    work_dir: Path = None,
    runtime_options: RuntimeOptions = None,
) -> Iterator[str]:
    """Ensemble every audio file in ``input_dir``. Yields one log line at a time.

    A failing file is reported and skipped; the rest of the batch keeps going.
    """
    check_ensemble(len(members), options.algorithm, options.weights)
    input_dir, output_dir = resolve_batch_dirs(input_dir, output_dir)
    files = list_audio_files(input_dir)
    if not files:
        yield "No valid audio files."
        return

    yield f"{len(files)} audio files found"
    progress(0, "Starting processing...")
    results = yield from _run(members, files, output_dir, output_format, options, cache, progress, work_dir,
                              runtime_options)
    failed = sum(isinstance(r, Exception) for r in results.values())
    progress(1.0, "Processing complete")
    yield f"Done: {len(files) - failed} ensembled, {failed} failed. Output: {output_dir}"


def _run(members, files, output_dir, output_format, options, cache, progress, work_dir, runtime_options,
         ) -> Generator[str, None, dict[Path, list[StemResult] | Exception]]:
    work_dir = Path(work_dir or default_work_dir())
    total_steps = len(files) * (len(members) + 1)  # one separation per model + combining, per file
    done_steps = 0
    results: dict[Path, list[StemResult] | Exception] = {}

    def step(desc: str) -> None:
        progress(done_steps / total_steps, desc)

    for start in range(0, len(files), GROUP_SIZE):
        group = files[start:start + GROUP_SIZE]
        shutil.rmtree(work_dir, ignore_errors=True)
        outputs: dict[Path, list[list[Path]]] = {file: [] for file in group}  # per file, per member
        failed: dict[Path, Exception] = {}
        try:
            for index, member in enumerate(members):
                member_dir = work_dir / f"model_{index + 1}"
                member_dir.mkdir(parents=True, exist_ok=True)
                step(f"Loading model {index + 1}/{len(members)}...")
                yield f"Loading model {index + 1}/{len(members)}: {member.model.id}"
                try:
                    with separation_lock:
                        separator = cache.get(member.spec, member.model, member.separator_values(), member_dir,
                                              "wav", options=runtime_options)
                except Exception as e:
                    cache.clear()
                    raise SeparationError(f"Could not load model {member.model.id}: {describe_error(e)}") from e
                if summary := execution_summary(separator):
                    yield f"Model loaded ({summary})"

                for file in group:
                    if file in failed:
                        done_steps += 1
                        continue
                    step(f"Model {index + 1}/{len(members)}: {file.name}")
                    yield f"Separating {file.name} with {member.model.id}"
                    try:
                        with separation_lock:
                            names = separator.separate(str(file))
                        if not names:
                            raise SeparationError("no output produced, check the console for details")
                        outputs[file].append([member_dir / name for name in names])
                    except Exception as e:
                        logger.warning("Ensemble separation of %s with %s failed: %s", file, member.model.id,
                                       describe_error(e))
                        failed[file] = e
                        yield f"Error separating {file.name}: {describe_error(e)}"
                    done_steps += 1

            for file in group:
                if file in failed:
                    results[file] = failed[file]
                    done_steps += 1
                    continue
                step(f"Combining stems: {file.name}")
                yield f"Combining stems of {file.name} ({options.algorithm})"
                try:
                    template = (runtime_options or RuntimeOptions()).name_template
                    results[file] = _combine(file, outputs[file], output_dir, output_format, options, template)
                    yield f"File: {file.name} ensembled!"
                except Exception as e:
                    logger.warning("Combining the stems of %s failed", file, exc_info=True)
                    results[file] = e
                    yield f"Error combining {file.name}: {describe_error(e)}"
                if options.keep_intermediates:
                    _keep_intermediates(file, outputs[file], output_dir)
                done_steps += 1
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    progress(1.0, "Ensemble complete")
    return results


def _combine(file: Path, member_outputs: list[list[Path]], output_dir: Path, output_format: str,
             options: EnsembleOptions, name_template: str = DEFAULT_NAME_TEMPLATE) -> list[StemResult]:
    # Imported lazily: audio_separator pulls in torch/onnxruntime at import time
    from audio_separator.separator.ensembler import Ensembler

    member_count = len(member_outputs)
    groups: dict[str, list[tuple[int, Path]]] = {}
    for index, stem_paths in enumerate(member_outputs):
        raw_names = [parse_stem_label(p.name) or "Unknown" for p in stem_paths]
        for path, raw in zip(stem_paths, raw_names):
            groups.setdefault(canonical_stem(raw, raw_names), []).append((index, path))

    def shared(items):
        return len({index for index, _ in items}) == member_count

    if not any(shared(items) for items in groups.values()) and not options.include_unmatched:
        found = ", ".join(sorted(groups)) or "none"
        raise SeparationError(
            f"The selected models have no stem in common (stems found: {found}). "
            "Choose models that separate the same stems or include the unmatched stems."
        )

    results = []
    # Stems every model produced first, each group in the order the models wrote them
    for stem, items in sorted(groups.items(), key=lambda group: not shared(group[1])):
        if not shared(items) and not options.include_unmatched:
            logger.info("Skipping stem %s of %s: not produced by every model", stem, file.name)
            continue
        waves = [load_audio(path, options.sample_rate) for _, path in items]
        mono = all(w.shape[0] == 1 for w in waves)
        waves = [np.vstack([w, w]) if w.shape[0] == 1 else w for w in waves]
        weights = None
        if options.weights is not None and options.algorithm in WEIGHTED_ALGORITHMS:
            weights = [float(options.weights[index]) for index, _ in items]
        combined = Ensembler(logger, options.algorithm, weights).ensemble(waves)
        # Spectrogram algorithms can return a few samples less: keep the members' length
        length = max(w.shape[1] for w in waves)
        combined = np.pad(combined, ((0, 0), (0, max(length - combined.shape[1], 0))))[:, :length]
        if mono:
            combined = combined[:1]
        combined = normalize_peak(combined, options.normalization_threshold, options.amplification_threshold)

        name = render_name(name_template, input=file.stem, stem=stem, model=f"ensemble_{options.label}")
        output = Path(output_dir) / f"{name}.{output_format}"
        write_audio(output, combined, options.sample_rate, subtype=audio_subtype(items[0][1]))
        results.append(StemResult(str(output), stem))
    return results


def _keep_intermediates(file: Path, member_outputs: list[list[Path]], output_dir: Path) -> None:
    target = Path(output_dir) / f"{file.stem}_ensemble_parts"
    target.mkdir(parents=True, exist_ok=True)
    for stem_paths in member_outputs:
        for path in stem_paths:
            if path.exists():
                shutil.move(str(path), str(target / path.name))
