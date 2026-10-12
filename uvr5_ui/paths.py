"""Filesystem locations, resolved from the package location instead of the CWD."""

import os
from pathlib import Path

ROOT = Path(os.environ.get("UVR5_UI_ROOT") or Path(__file__).resolve().parents[1])

ASSETS_DIR = ROOT / "assets"
LANG_DIR = ASSETS_DIR / "i18n" / "languages"
THEMES_DIR = ASSETS_DIR / "themes"
FAVICON = ASSETS_DIR / "favicon.ico"
DEFAULT_CONFIG_FILE = ASSETS_DIR / "config.default.json"
DEFAULT_SETTINGS_FILE = ASSETS_DIR / "default_settings.json"
MODELS_CATALOG_FILE = ASSETS_DIR / "models.json"

USER_DATA_DIR = ROOT / "user_data"
USER_CONFIG_FILE = USER_DATA_DIR / "config.json"
CUSTOM_SETTINGS_FILE = USER_DATA_DIR / "custom_settings.json"

# Pre-2.0 locations, migrated into USER_DATA_DIR on startup
LEGACY_CONFIG_FILE = ASSETS_DIR / "config.json"
LEGACY_CUSTOM_SETTINGS_FILE = ASSETS_DIR / "custom_settings.json"

MODELS_DIR = ROOT / "models"
OUTPUTS_DIR = ROOT / "outputs"
YTDL_DIR = ROOT / "ytdl"
