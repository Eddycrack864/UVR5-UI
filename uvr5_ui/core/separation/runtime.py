"""Creates audio-separator ``Separator`` instances and keeps the last loaded model warm.

Loading a model is the slow part of a separation, so the most recently used
Separator is cached and reused when the same model is run again with the same
settings (single files, consecutive runs, or every file of a batch).
"""

import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path

from uvr5_ui import hosting, paths
from uvr5_ui.core.audio import DEFAULT_NAME_TEMPLATE, check_name_template
from uvr5_ui.core.device import use_autocast
from uvr5_ui.core.downloads.model_downloader import ensure_downloaded
from uvr5_ui.core.models.catalog import Model
from uvr5_ui.core.separation.specs import ArchSpec, build_separator_kwargs

logger = logging.getLogger(__name__)

PRECISIONS = ("auto", "fp32", "autocast", "native_fp16")


@dataclass(frozen=True)
class RuntimeOptions:
    """Options shared by every separation: the "Performance" and "Output file names" settings."""

    precision: str = "auto"  # auto = autocast on CUDA, fp32 otherwise
    torch_compile: bool = False  # regional torch.compile of BS/Mel Roformer models
    chunk_duration: float = 0  # split inputs longer than this many seconds; 0 = never
    use_soundfile: bool = False  # write outputs with soundfile instead of pydub (less memory)
    name_template: str = DEFAULT_NAME_TEMPLATE  # applied after separating, not passed to Separator

    @classmethod
    def from_config(cls, config) -> "RuntimeOptions":
        precision = config.get("performance.precision", "auto")
        try:
            chunk_duration = max(float(config.get("performance.chunk_duration", 0) or 0), 0.0)
        except (TypeError, ValueError):
            chunk_duration = 0.0
        name_template = config.get("output.name_template") or DEFAULT_NAME_TEMPLATE
        try:
            check_name_template(name_template)
        except ValueError as e:
            logger.warning("Ignoring the output name template %r: %s", name_template, e)
            name_template = DEFAULT_NAME_TEMPLATE
        return cls(
            precision=precision if precision in PRECISIONS else "auto",
            # ZeroGPU doesn't support torch.compile
            torch_compile=bool(config.get("performance.torch_compile", False)) and not hosting.on_zerogpu(),
            chunk_duration=chunk_duration,
            use_soundfile=bool(config.get("performance.use_soundfile", False)),
            name_template=name_template,
        )

    def separator_kwargs(self) -> dict:
        precision = self.precision
        if precision == "auto":
            precision = "autocast" if use_autocast() else "fp32"
        return {
            "use_autocast": precision == "autocast",
            "use_native_fp16": precision == "native_fp16",
            "use_torch_compile": self.torch_compile,
            "chunk_duration": self.chunk_duration or None,
            "use_soundfile": self.use_soundfile,
        }


def execution_summary(separator) -> str | None:
    """What audio-separator actually enabled for the loaded model, e.g. ``native_fp16 + torch.compile``.

    Unsupported requests (fp16 on CPU, compile without Triton...) silently fall back,
    so this is what the user should see.
    """
    precision = getattr(separator, "effective_precision", None)
    if not isinstance(precision, str):
        return None
    return precision + (" + torch.compile" if getattr(separator, "effective_torch_compile", False) is True else "")


def _separator_class():
    # Imported lazily: audio_separator pulls in torch/onnxruntime at import time.
    from audio_separator.separator import Separator

    return Separator


class SeparatorCache:
    def __init__(self, factory=None):
        self._factory = factory
        self._key = None
        self._separator = None
        self._lock = threading.Lock()

    def get(self, spec: ArchSpec, model: Model, values: dict, output_dir: Path, output_format: str,
            models_dir: Path = None, options: RuntimeOptions = None, progress=None):
        """Return a Separator with ``model`` loaded, reusing the cached one when possible.

        Missing model files are downloaded first (``progress`` reports it), see ``ensure_downloaded``.
        """
        models_dir = Path(models_dir or paths.MODELS_DIR)
        kwargs = dict(
            log_level=logging.WARNING,
            model_file_dir=str(models_dir),
            output_dir=str(output_dir),
            output_format=output_format,
            **(options or RuntimeOptions()).separator_kwargs(),
            **build_separator_kwargs(spec, values),
        )
        key = (model.filename, json.dumps(kwargs, sort_keys=True, default=str))

        with self._lock:
            if self._key == key and self._separator is not None:
                logger.debug("Reusing loaded model %s", model.filename)
                return self._separator

            # Drop the previous model before loading a new one to free (GPU) memory.
            self._key = self._separator = None
            ensure_downloaded(model, models_dir, progress)
            factory = self._factory or _separator_class()
            separator = factory(**kwargs)
            separator.load_model(model_filename=model.filename)
            summary = execution_summary(separator)
            if summary:
                logger.info("Loaded %s (%s)", model.filename, summary)
            self._key, self._separator = key, separator
            return separator

    def clear(self) -> None:
        with self._lock:
            self._key = self._separator = None


separator_cache = SeparatorCache()

# Held around every model load and separation. Gradio already queues separations one at a
# time; this also covers a cancelled event whose worker thread is still finishing a file.
separation_lock = threading.Lock()
