"""Application config: versioned defaults merged with per-user overrides.

Defaults live in ``assets/config.default.json`` (tracked by git, never written).
Whatever the user changes is written to ``user_data/config.json`` (gitignored),
so the updater's ``git reset --hard`` no longer wipes user preferences.
"""

import copy
import json
import logging
import os
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Any

from uvr5_ui import paths

logger = logging.getLogger(__name__)

_MISSING = object()


def read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json_atomic(path: Path, data: Any, indent: int = 2) -> None:
    """Write JSON through a temp file + rename so a crash never leaves half a file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def deep_merge(base: dict, override: dict) -> dict:
    """Return a new dict with ``override`` merged recursively on top of ``base``."""
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


class ConfigStore:
    def __init__(self, defaults_file: Path = None, user_file: Path = None):
        self.defaults_file = Path(defaults_file or paths.DEFAULT_CONFIG_FILE)
        self.user_file = Path(user_file or paths.USER_CONFIG_FILE)
        self._lock = threading.Lock()
        self._defaults = self._read_or_empty(self.defaults_file)
        self._overrides = self._read_or_empty(self.user_file)

    @staticmethod
    def _read_or_empty(path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            data = read_json(path)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError) as e:
            logger.warning("Could not read config file '%s': %s", path, e)
            return {}

    @property
    def data(self) -> dict:
        return deep_merge(self._defaults, self._overrides)

    def get(self, key: str, default: Any = None) -> Any:
        """Read a dotted key, e.g. ``config.get("theme.mode")``."""
        node = self.data
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, key: str, value: Any) -> None:
        """Persist a dotted key into the user overrides file."""
        with self._lock:
            node = self._overrides
            parts = key.split(".")
            for part in parts[:-1]:
                child = node.get(part)
                if not isinstance(child, dict):
                    child = node[part] = {}
                node = child
            node[parts[-1]] = value
            write_json_atomic(self.user_file, self._overrides)


def migrate_legacy_user_data(
    legacy_config: Path = None,
    user_config: Path = None,
    legacy_custom_settings: Path = None,
    custom_settings: Path = None,
) -> list[str]:
    """Move pre-2.0 user files from ``assets/`` into ``user_data/``. Returns what was migrated."""
    legacy_config = Path(legacy_config or paths.LEGACY_CONFIG_FILE)
    user_config = Path(user_config or paths.USER_CONFIG_FILE)
    legacy_custom_settings = Path(legacy_custom_settings or paths.LEGACY_CUSTOM_SETTINGS_FILE)
    custom_settings = Path(custom_settings or paths.CUSTOM_SETTINGS_FILE)

    migrated = []
    if legacy_config.exists() and not user_config.exists():
        user_config.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_config, user_config)
        migrated.append(str(legacy_config))
    if legacy_custom_settings.exists() and not custom_settings.exists():
        custom_settings.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(legacy_custom_settings), str(custom_settings))
        migrated.append(str(legacy_custom_settings))
    for item in migrated:
        logger.info("Migrated legacy user file '%s' into '%s'", item, user_config.parent)
    return migrated


_store: ConfigStore | None = None


def get_config() -> ConfigStore:
    """Process-wide config store, created on first use."""
    global _store
    if _store is None:
        _store = ConfigStore()
    return _store
