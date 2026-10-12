"""Reusable Gradio widget factories. Must be called inside a ``gr.Blocks`` context."""

import gradio as gr

from uvr5_ui.core.separation.specs import ParamSpec
from uvr5_ui.i18n import N_, i18n

STEM_LABELS = (N_("Stem 1"), N_("Stem 2"), N_("Stem 3"), N_("Stem 4"), N_("Stem 5"), N_("Stem 6"))
MAX_STEMS = len(STEM_LABELS)


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
        )
    if param.widget == "checkbox":
        return gr.Checkbox(
            label=i18n(param.label),
            info=i18n(param.info) if param.info else None,
            value=value,
            interactive=True,
        )
    return single_line_textbox(i18n(param.label), i18n(param.placeholder) if param.placeholder else None, value or "")


def single_line_textbox(label: str, placeholder: str | None, value: str = ""):
    return gr.Textbox(label=label, placeholder=placeholder, value=value, lines=1, max_lines=1, interactive=True)


def output_log(label: str = None):
    return gr.Textbox(label=label or i18n("Output information"), lines=5, interactive=False)


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
                    show_download_button=True,
                    visible=index <= 2,
                ))
    return stems


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
