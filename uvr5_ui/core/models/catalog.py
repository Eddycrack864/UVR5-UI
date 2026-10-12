"""The model catalog (assets/models.json): which models each architecture offers."""

import functools
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from uvr5_ui import paths

logger = logging.getLogger(__name__)

SOURCES = ("github", "huggingface")


@dataclass(frozen=True)
class Model:
    id: str  # what the user sees in the dropdown
    arch: str
    filename: str  # what audio-separator loads
    sources: dict = field(default_factory=dict, compare=False, hash=False)

    def urls(self, source: str) -> list[str]:
        """Download URLs for ``source``, falling back to any other available source."""
        urls = self.sources.get(source)
        if urls:
            return list(urls)
        for other in SOURCES:
            if self.sources.get(other):
                return list(self.sources[other])
        return []


class ModelCatalog:
    def __init__(self, models: list[Model]):
        self._models = list(models)
        self._index = {(m.arch, m.id): m for m in self._models}

    @classmethod
    def from_file(cls, path: Path = None) -> "ModelCatalog":
        path = Path(path or paths.MODELS_CATALOG_FILE)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("version") != 2:
            raise ValueError(f"Unsupported model catalog version in {path}: {data.get('version')}")
        return cls(Model(m["id"], m["arch"], m["filename"], m.get("sources", {})) for m in data["models"])

    def __iter__(self):
        return iter(self._models)

    def __len__(self):
        return len(self._models)

    def by_arch(self, arch: str) -> list[Model]:
        return [m for m in self._models if m.arch == arch]

    def ids(self, arch: str) -> list[str]:
        return [m.id for m in self.by_arch(arch)]

    def get(self, arch: str, model_id: str) -> Model:
        try:
            return self._index[(arch, model_id)]
        except KeyError:
            raise KeyError(f"Unknown {arch} model: {model_id!r}") from None

    def find(self, model_id: str) -> Model | None:
        """Look a model up by id across all architectures."""
        return next((m for m in self._models if m.id == model_id), None)

    def downloaded(self, arch: str, models_dir: Path = None) -> list[Model]:
        models_dir = Path(models_dir or paths.MODELS_DIR)
        try:
            present = set(os.listdir(models_dir))
        except OSError as e:
            logger.warning("Could not read models directory '%s': %s", models_dir, e)
            return []
        return [m for m in self.by_arch(arch) if m.filename in present]

    def downloadable(self) -> list[Model]:
        return [m for m in self._models if any(m.sources.get(s) for s in SOURCES)]

    def is_downloaded(self, model: Model, models_dir: Path = None) -> bool:
        return (Path(models_dir or paths.MODELS_DIR) / model.filename).exists()


@functools.lru_cache(maxsize=1)
def get_catalog() -> ModelCatalog:
    return ModelCatalog.from_file()
