"""Screen reader support that Gradio doesn't give yet (issue #66).

- ``head_html()``: ``a11y.js`` in the page ``<head>``. It makes Gradio use the UVR5 UI
  language (its own texts and ``<html lang>``, which NVDA uses to pick the voice), adds the
  missing ARIA to accordions, announces validation messages and keeps the focus on a dropdown
  after choosing an option.
- ``CSS``: a visible keyboard focus with every theme.
- ``announcer()`` + ``announce()``: short messages for events that change the page silently
  (a finished separation, a refreshed model list), read through the same live region.
"""

import html
import json
import time
from pathlib import Path

import gradio as gr

from uvr5_ui.core.audio import parse_stem_label
from uvr5_ui.i18n import i18n

_HERE = Path(__file__).parent
CSS = (_HERE / "a11y.css").read_text(encoding="utf-8")

# Languages Gradio translates its own texts into (its frontend locale codes)
GRADIO_LOCALES = {
    "ar", "ca", "de", "en", "es", "et", "eu", "fa", "fr", "he", "id", "ja", "ko", "lt", "nb",
    "pt", "pt-BR", "ro", "ru", "sv", "ta", "th", "tr", "uk", "ur", "uz", "zh-CN", "zh-TW",
}


def page_language(language: str) -> str:
    """BCP 47 tag of a UVR5 UI language file name: ``es_ES`` -> ``es-ES``."""
    return language.replace("_", "-")


def gradio_locale(language: str) -> str:
    """The Gradio locale closest to a UVR5 UI language, English when Gradio has none."""
    tag = page_language(language)
    for candidate in (tag, tag.split("-")[0]):
        if candidate in GRADIO_LOCALES:
            return candidate
    return "en"


def gradio_i18n(language: str) -> gr.I18n:
    """Translations missing from Gradio itself.

    Its progress announcement for screen readers reads "common.complete", a key no Gradio
    language defines, so NVDA said "common.complete" after every action.
    """
    return gr.I18n(**{gradio_locale(language): {"common.complete": i18n("Complete")}})


def head_html(language: str) -> str:
    config = {"page_lang": page_language(language), "gradio_locale": gradio_locale(language)}
    script = (_HERE / "a11y.js").read_text(encoding="utf-8").replace("__CONFIG__", json.dumps(config))
    return f"<script>{script}</script>"


def tab_heading(label: str) -> gr.HTML:
    """A heading only screen readers see, so each tab can be reached with their heading keys (H)."""
    return gr.HTML(f"<h2>{html.escape(label)}</h2>", elem_classes=["uvr-sr-only"])


def announcer() -> gr.HTML:
    """Invisible component whose value is read aloud by screen readers when it changes."""
    return gr.HTML(
        value=None,
        html_template="",
        js_on_load="watch('value', () => props.value && window.uvr5Announce && window.uvr5Announce(props.value.text));",
        elem_classes=["uvr-announcer"],
    )


def announce(text: str) -> dict:
    # The id makes every message a new value, so a repeated one is announced again
    return {"text": text, "id": time.monotonic_ns()}


def announce_stems(*stem_paths):
    """Chained after a separation: which stems came out, e.g. "Separation finished: Vocals, Instrumental"."""
    labels = [parse_stem_label(path) or Path(path).stem for path in stem_paths if path]
    return announce(i18n("Separation finished: {stems}").format(stems=", ".join(labels)))


def announce_batch(log: str | None):
    """Chained after a batch: its summary line, e.g. "Done: 3 separated, 0 failed. Output: ..."."""
    summary = (log or "").strip().splitlines()[-1:] or [""]
    return announce(f"{i18n('Batch separation finished')}. {summary[0]}".strip())
