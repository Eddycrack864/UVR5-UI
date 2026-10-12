"""Separation parameter presets: bundled defaults plus an optional user preset.

Files are ``{section: {key: value}}`` where sections are the
``ArchSpec.settings_section`` names ("Roformer", "MDX23C", ...).
"""

import logging
from pathlib import Path
from typing import Any

from uvr5_ui import paths
from uvr5_ui.config.store import ConfigStore, deep_merge, get_config, read_json, write_json_atomic

logger = logging.getLogger(__name__)


class SeparationSettings:
    def __init__(self, config: ConfigStore = None, defaults_file: Path = None, custom_file: Path = None):
        self.config = config or get_config()
        self.defaults_file = Path(defaults_file or paths.DEFAULT_SETTINGS_FILE)
        self.custom_file = Path(custom_file or paths.CUSTOM_SETTINGS_FILE)

    def defaults(self) -> dict:
        return read_json(self.defaults_file)

    def initial(self) -> dict:
        """Settings to show at startup: the user preset if enabled, else the defaults."""
        defaults = self.defaults()
        if not self.config.get("load_custom_settings", False):
            return defaults
        try:
            custom = read_json(self.custom_file)
        except (OSError, ValueError) as e:
            logger.warning("Custom settings '%s' not found or invalid, using defaults: %s", self.custom_file, e)
            return defaults
        return deep_merge(defaults, custom)

    def save_custom(self, data: dict) -> None:
        write_json_atomic(self.custom_file, data, indent=4)
        self.config.set("load_custom_settings", True)

    def reset(self) -> dict:
        self.config.set("load_custom_settings", False)
        return self.defaults()

    @staticmethod
    def value(settings: dict, section: str, key: str, fallback: Any = None) -> Any:
        return settings.get(section, {}).get(key, fallback)
