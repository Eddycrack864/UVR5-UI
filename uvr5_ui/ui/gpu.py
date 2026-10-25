"""Runs separations, with a GPU attached on ZeroGPU Spaces (see ``hosting``).

On ZeroGPU, ``separate`` and ``ensemble`` run in a worker process: their arguments are pickled, so
they take plain data and the ``gr.Progress`` itself (spaces forwards its updates to the page).
Anywhere else they are plain function calls.
"""

import logging
import shutil
import time
import uuid
from pathlib import Path

import gradio as gr

from uvr5_ui import hosting, paths
from uvr5_ui.core.downloads.model_downloader import ensure_downloaded
from uvr5_ui.core.separation.ensemble import ensemble_file
from uvr5_ui.core.separation.service import separate_file
from uvr5_ui.core.separation.specs import ARCHITECTURES_BY_ID
from uvr5_ui.ui.adapters import progress_callback

logger = logging.getLogger(__name__)

# GPU time requested per model. ZeroGPU checks it against the visitor's remaining daily quota
# before running, so ask for what a separation realistically needs, not more.
BASE_SECONDS = 20  # loading the model
SECONDS_PER_AUDIO_SECOND = 0.2
MAX_SECONDS = 300
UNKNOWN_AUDIO_SECONDS = 240  # when the length can't be read

# Visitors of a Space each get their own output folder, deleted after this many seconds
OUTPUT_MAX_AGE = 3600


def audio_seconds(audio_path: str) -> float:
    try:
        import soundfile

        return soundfile.info(audio_path).duration
    except Exception:
        pass
    try:
        import librosa

        return librosa.get_duration(path=audio_path)
    except Exception:
        return UNKNOWN_AUDIO_SECONDS


def gpu_seconds(audio_path: str, model_count: int = 1) -> int:
    per_model = BASE_SECONDS + SECONDS_PER_AUDIO_SECOND * audio_seconds(audio_path)
    return int(min(MAX_SECONDS, per_model * max(model_count, 1)))


def _separate(spec_id, model, audio_path, output_format, values, options, output_dir, progress):
    return separate_file(ARCHITECTURES_BY_ID[spec_id], model, audio_path, output_format, values,
                         output_dir=output_dir, progress=progress_callback(progress), options=options)


def _separate_duration(spec_id, model, audio_path, *args):
    return gpu_seconds(audio_path)


def _ensemble(members, audio_path, output_format, options, runtime_options, output_dir, progress):
    return ensemble_file(members, audio_path, output_format, options, output_dir=output_dir,
                         progress=progress_callback(progress), runtime_options=runtime_options)


def _ensemble_duration(members, audio_path, *args):
    return gpu_seconds(audio_path, len(members))


separate = hosting.gpu(_separate, duration=_separate_duration)
ensemble = hosting.gpu(_ensemble, duration=_ensemble_duration)


def prefetch(models, progress: gr.Progress) -> None:
    """On ZeroGPU, download the models before asking for a GPU, so downloads don't use GPU time."""
    if not hosting.on_zerogpu():
        return  # separate()/ensemble() download them when they load the model
    report = progress_callback(progress)
    for model in models:
        ensure_downloaded(model, paths.MODELS_DIR, report)


def output_dir() -> Path | None:
    """Where a separation writes its stems: a folder of its own on a Space, ``outputs/`` otherwise."""
    if not hosting.on_space():
        return None
    _delete_old_outputs()
    folder = paths.OUTPUTS_DIR / uuid.uuid4().hex
    folder.mkdir(parents=True)
    return folder


def _delete_old_outputs() -> None:
    if not paths.OUTPUTS_DIR.is_dir():
        return
    limit = time.time() - OUTPUT_MAX_AGE
    for folder in paths.OUTPUTS_DIR.iterdir():
        try:
            if folder.is_dir() and folder.stat().st_mtime < limit:
                shutil.rmtree(folder, ignore_errors=True)
        except OSError as e:
            logger.debug("Could not delete %s: %s", folder, e)
