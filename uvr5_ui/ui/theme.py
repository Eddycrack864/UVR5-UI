"""Gradio theme selection.

Themes are either ids of themes hosted on the Hugging Face Hub (listed in
``assets/themes/themes_list.json``) or local ``.py`` files dropped into
``assets/themes/`` that define a ``gr.themes.Base`` subclass.
"""

import ast
import importlib.util
import json
import logging
from pathlib import Path

from uvr5_ui import paths
from uvr5_ui.config.store import ConfigStore, get_config

logger = logging.getLogger(__name__)

DEFAULT_THEME = "NoCrypt/miku"
MODES = ["light", "dark"]


def _find_theme_class(file_path: Path) -> str | None:
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            return node.name
    return None


def _local_theme_files(themes_dir: Path) -> list[Path]:
    return sorted(p for p in themes_dir.glob("*.py") if not p.name.startswith("_"))


def list_themes(themes_dir: Path = None) -> list[str]:
    themes_dir = Path(themes_dir or paths.THEMES_DIR)
    local = [p.stem for p in _local_theme_files(themes_dir)]
    try:
        with open(themes_dir / "themes_list.json", "r", encoding="utf-8") as f:
            remote = [item["id"] for item in json.load(f)]
    except FileNotFoundError:
        remote = []
    return list(dict.fromkeys(local + remote))


def select_theme(name: str, config: ConfigStore = None, themes_dir: Path = None) -> bool:
    """Persist the selected theme. Returns False if a local theme file has no class."""
    config = config or get_config()
    themes_dir = Path(themes_dir or paths.THEMES_DIR)
    file_path = themes_dir / f"{name}.py"

    if not file_path.exists():
        config.set("theme.file", None)
        config.set("theme.class", name)
        return True

    class_name = _find_theme_class(file_path)
    if not class_name:
        logger.warning("Theme file '%s' does not define a class", file_path)
        return False
    config.set("theme.file", file_path.name)
    config.set("theme.class", class_name)
    return True


def select_mode(mode: str, config: ConfigStore = None) -> None:
    (config or get_config()).set("theme.mode", mode)


def current_theme_name(config: ConfigStore = None) -> str:
    config = config or get_config()
    theme_file = config.get("theme.file")
    class_name = config.get("theme.class")
    if theme_file and class_name:
        return Path(theme_file).stem
    return class_name or DEFAULT_THEME


def current_mode(config: ConfigStore = None) -> str:
    mode = (config or get_config()).get("theme.mode", "dark")
    return mode if mode in MODES else "dark"


def load_theme(config: ConfigStore = None, themes_dir: Path = None):
    """Return a theme instance (local file), a Hub theme id (str) or None."""
    config = config or get_config()
    themes_dir = Path(themes_dir or paths.THEMES_DIR)
    theme_file = config.get("theme.file")
    class_name = config.get("theme.class")

    if not class_name:
        return None
    if not theme_file:
        return class_name

    try:
        file_path = themes_dir / theme_file
        spec = importlib.util.spec_from_file_location(f"uvr5_ui_theme_{file_path.stem}", file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        theme = getattr(module, class_name)()
        logger.info("Theme %s successfully loaded.", class_name)
        return theme
    except Exception as e:
        logger.error("An error occurred loading the theme '%s': %s", theme_file, e)
        return None


def mode_js(mode: str) -> str:
    """JS that forces Gradio's ``__theme`` URL param so light/dark mode applies on load."""
    return f"""
function refresh() {{
    const url = new URL(window.location);

    if (url.searchParams.get('__theme') !== '{mode}') {{
        url.searchParams.set('__theme', '{mode}');
        window.location.href = url.href;
    }}
}}
"""
