"""Stem mixer: plays every stem of a separation in sync, with a volume per stem.

Gradio has no component for this, so it is a ``gr.HTML`` driven by ``stem_mixer.js``
(Web Audio API). Its value holds the stems as ``FileData``: Gradio copies them to its
cache and gives the browser a URL that works behind proxies (Colab, --share, Spaces).
"""

from pathlib import Path

import gradio as gr
import soundfile

from uvr5_ui.core.audio import parse_stem_label
from uvr5_ui.i18n import i18n

MIN_STEMS = 2  # a single stem has nothing to mix
_HERE = Path(__file__).parent


def _read(name: str) -> str:
    return (_HERE / name).read_text(encoding="utf-8")


def stem_mixer() -> tuple[gr.Accordion, gr.HTML]:
    """A closed "Stem mixer" accordion, hidden until a separation gives two or more stems."""
    with gr.Accordion(i18n("Stem mixer"), open=False, visible=False) as accordion:
        gr.Markdown(i18n("Play all the stems together and adjust the volume of each one"))
        mixer = gr.HTML(
            value=None,
            html_template='<div class="uvr-mixer"></div>',
            css_template=_read("stem_mixer.css"),
            js_on_load=_read("stem_mixer.js"),
            labels={
                "play": i18n("Play"),
                "pause": i18n("Pause"),
                "stop": i18n("Stop"),
                "mute": i18n("Mute"),
                "solo": i18n("Solo"),
                "volume": i18n("Volume"),
                "position": i18n("Position"),
                "export": i18n("Download mix (.wav)"),
                "loading": i18n("Loading stems..."),
                "unplayable": i18n("This stem can't be played in the browser"),
            },
        )
    return accordion, mixer


def mixer_value(audio_path: str | None, stem_paths) -> dict | None:
    """The mixer's value for the stems shown in the output players, or None with fewer than two."""
    stems = [
        {
            # Output names can follow a custom template, so fall back to the file name
            "label": parse_stem_label(path) or Path(path).stem,
            "file": {"path": path, "meta": {"_type": "gradio.FileData"}},
        }
        for path in stem_paths if path
    ]
    if len(stems) < MIN_STEMS:
        return None
    return {
        "name": f"{Path(audio_path).stem if audio_path else 'stems'}_mix",
        # Playing and mixing at the stems' own rate, so the browser doesn't resample them
        "sample_rate": _sample_rate(stems[0]["file"]["path"]),
        "stems": stems,
    }


def _sample_rate(path: str) -> int | None:
    try:
        return soundfile.info(path).samplerate
    except Exception:  # not readable by libsndfile (e.g. m4a): the browser picks the rate
        return None


def mixer_update(audio_path, *stem_paths):
    """Chained after a separation: refresh the mixer and show it only when there is something to mix."""
    value = mixer_value(audio_path, stem_paths)
    return gr.update(visible=value is not None), value
