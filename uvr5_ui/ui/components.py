"""Reusable Gradio widget factories. Must be called inside a ``gr.Blocks`` context."""

import tempfile
from dataclasses import dataclass
from pathlib import Path

import gradio as gr

from uvr5_ui.core.audio import zip_files
from uvr5_ui.core.downloads.ytdl import download_audio
from uvr5_ui.core.models.catalog import Model, ModelCatalog
from uvr5_ui.core.separation.specs import ParamSpec
from uvr5_ui.i18n import N_, i18n
from uvr5_ui.ui.adapters import user_errors

STEM_LABELS = (N_("Stem 1"), N_("Stem 2"), N_("Stem 3"), N_("Stem 4"), N_("Stem 5"), N_("Stem 6"))
MAX_STEMS = len(STEM_LABELS)


def model_label(catalog: ModelCatalog, model: Model, prefix: str = "") -> str:
    """Dropdown label of a model: its id, plus e.g. ``(Vocals ⭐)`` when it is a recommended model."""
    stems = catalog.recommended_stems(model)
    return f"{prefix}{model.id} ({', '.join(stems)} ⭐)" if stems else prefix + model.id


def model_choices(catalog: ModelCatalog, models: list[Model]) -> list[tuple[str, str]]:
    """``(label, id)`` dropdown choices, recommended models first."""
    return [(model_label(catalog, m), m.id) for m in catalog.recommended_first(models)]


def param_widget(param: ParamSpec, value):
    value = param.default if value is None and param.widget != "textbox" else value
    if param.widget == "slider":
        return gr.Slider(
            label=i18n(param.label),
            info=i18n(param.info) if param.info else None,
            minimum=param.minimum,
            maximum=param.maximum,
            step=param.step,
            value=value,
            interactive=True,
            visible=param.visible,
        )
    if param.widget == "checkbox":
        return gr.Checkbox(
            label=i18n(param.label),
            info=i18n(param.info) if param.info else None,
            value=value,
            interactive=True,
            visible=param.visible,
        )
    return single_line_textbox(i18n(param.label), i18n(param.placeholder) if param.placeholder else None, value or "",
                               visible=param.visible)


def single_line_textbox(label: str, placeholder: str | None, value: str = "", visible: bool = True):
    return gr.Textbox(label=label, placeholder=placeholder, value=value, lines=1, max_lines=1, interactive=True,
                      visible=visible)


def output_log(label: str = None):
    return gr.Textbox(label=label or i18n("Output information"), lines=5, interactive=False)


@dataclass
class InputSections:
    audio: gr.Audio
    link: gr.Textbox
    input_path: gr.Textbox
    output_path: gr.Textbox
    batch_button: gr.Button
    stop_button: gr.Button
    batch_info: gr.Textbox

    def wire_stop(self, batch_event) -> None:
        """Let the stop button cancel ``batch_event``; the file being separated still finishes."""
        self.stop_button.click(None, cancels=[batch_event], api_visibility="undocumented")


def input_sections(section: dict, api_suffix: str) -> InputSections:
    """Input audio plus the "Separation by link" and "Batch separation" accordions of a separation tab."""
    with gr.Row():
        audio = gr.Audio(label=i18n("Input audio"), type="filepath", interactive=True)

    with gr.Accordion(i18n("Separation by link"), open=False):
        with gr.Row():
            link = single_line_textbox(i18n("Link"), i18n("Paste the link here"), section.get("link", ""))
        with gr.Row():
            gr.Markdown(i18n("You can paste the link to the video/audio from many sites, check the complete list [here](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)"))
        with gr.Row():
            download_button = gr.Button(i18n("Download!"), variant="primary")

    with gr.Accordion(i18n("Batch separation"), open=False):
        with gr.Row():
            input_path = single_line_textbox(
                i18n("Input path"), i18n("Place the input path here"), section.get("input_path", "")
            )
            output_path = single_line_textbox(
                i18n("Output path"), i18n("Place the output path here"), section.get("output_path", "")
            )
        with gr.Row():
            batch_button = gr.Button(i18n("Separate all files!"), variant="primary")
            stop_button = gr.Button(i18n("Stop"), variant="stop")
        with gr.Row():
            batch_info = output_log()

    download_button.click(user_errors(lambda url: str(download_audio(url))), inputs=[link], outputs=[audio],
                          api_name=f"download_link_{api_suffix}")
    return InputSections(audio, link, input_path, output_path, batch_button, stop_button, batch_info)


def stem_outputs() -> list[gr.Audio]:
    """Six output players in rows of two. Only the first two are visible until a result arrives."""
    stems = []
    for row in range(MAX_STEMS // 2):
        with gr.Row():
            for col in range(2):
                index = row * 2 + col + 1
                stems.append(gr.Audio(
                    label=i18n(STEM_LABELS[index - 1]),
                    type="filepath",
                    interactive=False,
                    buttons=["download"],
                    visible=index <= 2,
                ))
    return stems


def zip_download() -> gr.DownloadButton:
    """Downloads every stem of the last separation at once. Hidden until there is a result."""
    return gr.DownloadButton(i18n("Download all stems (.zip)"), variant="secondary", visible=False)


def zip_update(results, audio_path: str):
    name = Path(audio_path or "stems").stem
    archive = zip_files([r.path for r in results], Path(tempfile.gettempdir()) / "uvr5_ui-zips" / f"{name}_stems.zip")
    return gr.update(value=str(archive), visible=True) if archive else gr.update(value=None, visible=False)


def stem_updates(results) -> list:
    """``gr.update`` for each of the six players from a list of ``StemResult``."""
    updates = []
    for i in range(MAX_STEMS):
        label = i18n(STEM_LABELS[i])
        if i < len(results):
            result = results[i]
            if result.label:
                label = f"{label} ({result.label})"
            updates.append(gr.update(value=result.path, label=label, visible=True))
        else:
            updates.append(gr.update(value=None, label=label, visible=i < 2))
    return updates
