"""Translations. The English source string is the lookup key in every language file."""

import json
import locale
import logging
from pathlib import Path

from uvr5_ui import paths
from uvr5_ui.config.store import ConfigStore, get_config

logger = logging.getLogger(__name__)

FALLBACK_LANGUAGE = "en_US"
AUTO_LANGUAGE = "Language automatically detected by system"


def N_(text: str) -> str:
    """Mark a string for translation without translating it yet.

    Used in declarative specs whose labels are translated later at render time,
    so ``tools/i18n_scan.py`` can still find them.
    """
    return text


def _system_locale() -> str | None:
    try:
        lang = locale.getlocale()[0]
    except ValueError:
        lang = None
    if not lang:
        try:
            lang = locale.getdefaultlocale()[0]
        except ValueError:
            lang = None
    return lang


class I18nAuto:
    def __init__(self, language: str = None, config: ConfigStore = None, lang_dir: Path = None):
        self.lang_dir = Path(lang_dir or paths.LANG_DIR)
        config = config or get_config()

        if language is None and config.get("lang.override", False):
            language = config.get("lang.selected_lang", FALLBACK_LANGUAGE)
        if language is None or not self.language_exists(language):
            language = self._match_system_language(language)

        self.language = language
        self.language_map = self._load_language(language)

    def _match_system_language(self, requested: str | None) -> str:
        system = requested or _system_locale()
        prefix = system[:2].lower() if system else "en"
        matches = [lang for lang in self.available_languages() if lang.lower().startswith(prefix)]
        return matches[0] if matches else FALLBACK_LANGUAGE

    def _load_language(self, language: str) -> dict:
        file_path = self.lang_dir / f"{language}.json"
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            logger.warning("Language file '%s' not found, using source strings", file_path)
            return {}

    def available_languages(self) -> list[str]:
        return sorted(path.stem for path in self.lang_dir.glob("*.json"))

    def language_exists(self, language: str) -> bool:
        return (self.lang_dir / f"{language}.json").exists()

    def __call__(self, key: str) -> str:
        return self.language_map.get(key, key)


class _LazyI18n:
    """Module-level ``i18n`` that loads the language on first use, not at import."""

    _instance: I18nAuto | None = None

    def _get(self) -> I18nAuto:
        if self._instance is None:
            self._instance = I18nAuto()
        return self._instance

    def reset(self, instance: I18nAuto = None) -> None:
        self._instance = instance

    def __call__(self, key: str) -> str:
        return self._get()(key)

    def __getattr__(self, name):
        return getattr(self._get(), name)


i18n = _LazyI18n()
