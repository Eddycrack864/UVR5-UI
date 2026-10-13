"""Ensemble presets: the curated ones shipped with audio-separator plus the user's own.

Both files use audio-separator's ``ensemble_presets.json`` schema (version 1), so a
user preset can be contributed upstream as is. Presets reference models by filename.
"""

import importlib.util
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from uvr5_ui import paths
from uvr5_ui.config.store import read_json, write_json_atomic
from uvr5_ui.core.separation.ensemble import DEFAULT_ALGORITHM, EnsembleConfigError, check_ensemble

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
USER_PREFIX = "user_"  # user preset ids never collide with the bundled ones


@dataclass(frozen=True)
class EnsemblePreset:
    id: str
    name: str
    models: tuple[str, ...]  # model filenames
    algorithm: str = DEFAULT_ALGORITHM
    weights: tuple[float, ...] | None = None
    description: str = ""
    contributor: str = ""

    @property
    def is_user(self) -> bool:
        return self.id.startswith(USER_PREFIX)

    def to_json(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "models": list(self.models),
            "algorithm": self.algorithm,
            "weights": list(self.weights) if self.weights is not None else None,
            "contributor": self.contributor,
        }


def bundled_presets_file() -> Path | None:
    """audio-separator's ``ensemble_presets.json``, located without importing the package (that imports torch)."""
    spec = importlib.util.find_spec("audio_separator")
    if spec is None or not spec.submodule_search_locations:
        return None
    for location in spec.submodule_search_locations:
        path = Path(location) / "ensemble_presets.json"
        if path.is_file():
            return path
    return None


def parse_presets(data: dict, source: str = "presets") -> list[EnsemblePreset]:
    """Valid presets of a presets file. Invalid entries are logged and skipped."""
    presets = []
    for preset_id, raw in ((data or {}).get("presets") or {}).items():
        try:
            weights = raw.get("weights")
            preset = EnsemblePreset(
                id=preset_id,
                name=raw.get("name") or preset_id,
                models=tuple(raw["models"]),
                algorithm=raw.get("algorithm") or DEFAULT_ALGORITHM,
                weights=tuple(float(w) for w in weights) if weights is not None else None,
                description=raw.get("description") or "",
                contributor=raw.get("contributor") or "",
            )
            check_ensemble(len(preset.models), preset.algorithm, preset.weights)
        except (AttributeError, KeyError, TypeError, ValueError, EnsembleConfigError) as e:
            logger.warning("Skipping invalid ensemble preset '%s' from %s: %s", preset_id, source, e)
            continue
        presets.append(preset)
    return presets


def preset_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return USER_PREFIX + (slug or "preset")


class PresetStore:
    def __init__(self, user_file: Path = None, bundled_file: Path = None):
        self.user_file = Path(user_file or paths.USER_ENSEMBLE_PRESETS_FILE)
        self.bundled_file = bundled_file if bundled_file is not None else bundled_presets_file()

    def _read(self, path: Path | None) -> dict:
        if path is None or not Path(path).exists():
            return {}
        try:
            return read_json(path)
        except (OSError, ValueError) as e:
            logger.warning("Could not read ensemble presets '%s': %s", path, e)
            return {}

    def bundled(self) -> list[EnsemblePreset]:
        return parse_presets(self._read(self.bundled_file), str(self.bundled_file))

    def user(self) -> list[EnsemblePreset]:
        return parse_presets(self._read(self.user_file), str(self.user_file))

    def all(self) -> list[EnsemblePreset]:
        """Bundled presets first (in file order), then the user's."""
        return self.bundled() + self.user()

    def get(self, preset_id_: str) -> EnsemblePreset | None:
        return next((p for p in self.all() if p.id == preset_id_), None)

    def save(self, name: str, models: Sequence[str], algorithm: str, weights: Sequence[float] | None = None,
             description: str = "") -> EnsemblePreset:
        """Create or overwrite (same name) a user preset."""
        name = (name or "").strip()
        if not name:
            raise EnsembleConfigError("name", "A preset needs a name")
        weights = tuple(float(w) for w in weights) if weights is not None else None
        check_ensemble(len(models), algorithm, weights)
        preset = EnsemblePreset(preset_id(name), name, tuple(models), algorithm, weights, description.strip(),
                                contributor="UVR5 UI user")
        data = self._read(self.user_file) or {}
        data["version"] = SCHEMA_VERSION
        data.setdefault("presets", {})[preset.id] = preset.to_json()
        write_json_atomic(self.user_file, data, indent=4)
        return preset

    def delete(self, preset_id_: str) -> bool:
        """Delete a user preset. Bundled presets can't be deleted."""
        data = self._read(self.user_file)
        if not preset_id_.startswith(USER_PREFIX) or preset_id_ not in (data.get("presets") or {}):
            return False
        del data["presets"][preset_id_]
        write_json_atomic(self.user_file, data, indent=4)
        return True
