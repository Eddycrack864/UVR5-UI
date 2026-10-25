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
RECOMMENDED_FILE_NAME = "recommended_models.json"  # next to models.json


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
    def __init__(self, models: list[Model], recommended: dict[str, str] = None):
        self._models = list(models)
        self._index = {(m.arch, m.id): m for m in self._models}
        self._by_filename = {m.filename: m for m in self._models}
        # Top 1 model per stem ({stem: model id}, in display order), see recommended_models.json
        self._recommended: dict[str, list[str]] = {}  # model filename -> stems
        for stem, model_id in (recommended or {}).items():
            model = self.find(model_id)
            if model is None:
                logger.warning("Recommended %s model %r is not in the catalog", stem, model_id)
                continue
            self._recommended.setdefault(model.filename, []).append(stem)

    @classmethod
    def from_file(cls, path: Path = None, recommended_path: Path = None) -> "ModelCatalog":
        path = Path(path or paths.MODELS_CATALOG_FILE)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("version") != 2:
            raise ValueError(f"Unsupported model catalog version in {path}: {data.get('version')}")
        models = [Model(m["id"], m["arch"], m["filename"], m.get("sources", {})) for m in data["models"]]
        return cls(models, load_recommended(recommended_path or path.with_name(RECOMMENDED_FILE_NAME)))

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

    def by_filename(self, filename: str) -> Model | None:
        """Look a model up by the file audio-separator loads (unique across the catalog)."""
        return self._by_filename.get(filename)

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

    def recommended_stems(self, model: Model) -> list[str]:
        """The stems ``model`` is the recommended (Top 1) model for, e.g. ``["Vocals"]``."""
        return self._recommended.get(model.filename, [])

    def recommended_first(self, models: list[Model]) -> list[Model]:
        """``models`` with the recommended ones first (in recommended_models.json order)."""
        rank = {filename: i for i, filename in enumerate(self._recommended)}
        return sorted(models, key=lambda m: rank.get(m.filename, len(rank)))


def load_recommended(path: Path) -> dict[str, str]:
    """``{stem: model id}`` from recommended_models.json; empty when the file is missing or invalid."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as e:
        logger.warning("Could not read recommended models from '%s': %s", path, e)
        return {}
    recommended = data.get("recommended") if isinstance(data, dict) else None
    return recommended if isinstance(recommended, dict) else {}


@functools.lru_cache(maxsize=1)
def get_catalog() -> ModelCatalog:
    return ModelCatalog.from_file()
