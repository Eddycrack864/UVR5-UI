"""Creates audio-separator ``Separator`` instances and keeps the last loaded model warm.

Loading a model is the slow part of a separation, so the most recently used
Separator is cached and reused when the same model is run again with the same
settings (single files, consecutive runs, or every file of a batch).
"""

import json
import logging
import threading
from pathlib import Path

from uvr5_ui import paths
from uvr5_ui.core.device import use_autocast
from uvr5_ui.core.models.catalog import Model
from uvr5_ui.core.separation.specs import ArchSpec, build_separator_kwargs

logger = logging.getLogger(__name__)


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
            models_dir: Path = None):
        """Return a Separator with ``model`` loaded, reusing the cached one when possible."""
        models_dir = Path(models_dir or paths.MODELS_DIR)
        kwargs = dict(
            log_level=logging.WARNING,
            model_file_dir=str(models_dir),
            output_dir=str(output_dir),
            output_format=output_format,
            use_autocast=use_autocast(),
            **build_separator_kwargs(spec, values),
        )
        key = (model.filename, json.dumps(kwargs, sort_keys=True, default=str))

        with self._lock:
            if self._key == key and self._separator is not None:
                logger.debug("Reusing loaded model %s", model.filename)
                return self._separator

            # Drop the previous model before loading a new one to free (GPU) memory.
            self._key = self._separator = None
            factory = self._factory or _separator_class()
            separator = factory(**kwargs)
            separator.load_model(model_filename=model.filename)
            self._key, self._separator = key, separator
            return separator

    def clear(self) -> None:
        with self._lock:
            self._key = self._separator = None


separator_cache = SeparatorCache()
