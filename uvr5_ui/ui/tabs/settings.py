import logging

import gradio as gr

from uvr5_ui.core.audio import DEFAULT_NAME_TEMPLATE, check_name_template
from uvr5_ui.core.device import get_device
from uvr5_ui.core.downloads.model_downloader import METHOD_PYTHON, METHODS, SOURCES, download_model
from uvr5_ui.core.separation.runtime import RuntimeOptions
from uvr5_ui.i18n import AUTO_LANGUAGE, LANGUAGE_NAMES, N_, i18n, normalize_language
from uvr5_ui.ui import a11y
from uvr5_ui.ui.adapters import progress_callback, require, user_errors
from uvr5_ui.ui.components import model_choices, output_log
from uvr5_ui.ui.context import AppContext
from uvr5_ui.ui.tabs.separation import DEFAULT_OUTPUT_FORMAT, SeparationTab

logger = logging.getLogger(__name__)


def render_settings_tab(ctx: AppContext, separation_tabs: list[SeparationTab]) -> None:
    with gr.TabItem(i18n("Settings")):
        a11y.tab_heading(i18n("Settings"))
        with gr.Accordion(i18n("Language selector"), open=False):
            selected_language = gr.Dropdown(
                label=i18n("Language"),
                info=i18n("Select the language you want to use. (Requires restarting the App)"),
                value=_current_language(ctx),
                # Names instead of bare codes, which screen readers spell out ("a r underscore A R")
                choices=[(i18n("Language automatically detected by system"), AUTO_LANGUAGE)]
                + [(f"{LANGUAGE_NAMES.get(code, code)} ({code})", code) for code in i18n.available_languages()],
                interactive=True,
            )

        with gr.Accordion(i18n("Alternative model downloader"), open=False):
            download_method = gr.Dropdown(
                label=i18n("Download method"),
                info=i18n("Select the download method you want to use. (Must have it installed)"),
                value=METHOD_PYTHON,
                choices=METHODS,
                interactive=True,
            )
            download_source = gr.Dropdown(
                label=i18n("Download source"),
                info=i18n("Select the source to download the model from (Github or Hugging Face)"),
                value=lambda: None,
                choices=list(SOURCES),
                interactive=True,
            )
            model_to_download = gr.Dropdown(
                label=i18n("Model to download"),
                info=i18n("Select the model to download using the selected method"),
                value=lambda: None,
                choices=model_choices(ctx.catalog, ctx.catalog.downloadable()),
                interactive=True,
            )
            download_button = gr.Button(i18n("Download!"), variant="primary")
            download_output = output_log()

        with gr.Accordion(i18n("Performance"), open=False):
            runtime = RuntimeOptions.from_config(ctx.config)
            precision = gr.Dropdown(
                label=i18n("Precision"),
                info=i18n("Native FP16 makes BS/Mel Roformer models faster and lighter on NVIDIA and Apple GPUs. "
                          "Unsupported combinations fall back to FP32."),
                choices=[(i18n("Automatic (autocast on CUDA)"), "auto"), ("FP32", "fp32"), ("Autocast", "autocast"),
                         (i18n("Native FP16"), "native_fp16")],
                value=runtime.precision,
                interactive=True,
            )
            torch_compile = gr.Checkbox(
                label=i18n("Compile BS/Mel Roformer models (torch.compile)"),
                info=i18n("Experimental: speeds up long or repeated separations, but the first one is slower. "
                          "Needs Triton (Linux, Colab); without it, it is skipped."),
                value=runtime.torch_compile,
                interactive=True,
            )
            chunk_duration = gr.Number(
                label=i18n("Process long audio in chunks (seconds)"),
                info=i18n("0 = disabled. Use 600 for audio longer than an hour to avoid running out of memory. "
                          "Chunks are joined without a crossfade."),
                value=runtime.chunk_duration,
                minimum=0,
                step=60,
                precision=0,
                interactive=True,
            )
            use_soundfile = gr.Checkbox(
                label=i18n("Write outputs with soundfile"),
                info=i18n("Uses less memory when writing very long files"),
                value=runtime.use_soundfile,
                interactive=True,
            )
            gr.Markdown(i18n("Changes apply to the next separation."))

        with gr.Accordion(i18n("Output file names"), open=False):
            name_template = gr.Textbox(
                label=i18n("Name template"),
                info=i18n("Placeholders: {input} = input file name, {stem} = stem (required), {model} = model. "
                          "Press Enter to save."),
                value=runtime.name_template,
                placeholder=DEFAULT_NAME_TEMPLATE,
                lines=1,
                max_lines=1,
                interactive=True,
            )

        with gr.Accordion(i18n("Separation settings management"), open=False):
            gr.Markdown(i18n("Save your current separation parameter settings or reset them to the application defaults"))
            with gr.Row():
                save_button = gr.Button(i18n("Save current settings"), variant="primary")
                reset_button = gr.Button(i18n("Reset settings to default"), variant="primary")

        with gr.Accordion(i18n("Discord Rich Presence"), open=False):
            discord_presence = gr.Checkbox(
                label=i18n("Show UVR5 UI activity on Discord (Requires restarting the App)"),
                value=bool(ctx.config.get("discord_presence", False)),
                interactive=True,
            )

        gr.Markdown(f"{i18n('Device')}: `{get_device()}`")

    # Language
    def save_language(language):
        if language == AUTO_LANGUAGE:
            ctx.config.set("lang.override", False)
        else:
            ctx.config.set("lang.override", True)
            ctx.config.set("lang.selected_lang", language)
        gr.Info(i18n("Language have been saved. Restart UVR5 UI to apply the changes"))

    selected_language.change(save_language, inputs=[selected_language], api_visibility="undocumented")

    # Alternative model downloader
    @user_errors
    def run_download(method, source, model_id, progress=gr.Progress()):
        require(model_id, N_("Please select a model first"))
        model = ctx.catalog.find(model_id)
        lines = []
        for line in download_model(model, source, method or METHOD_PYTHON, progress=progress_callback(progress)):
            lines.append(line)
            yield "\n".join(lines)

    download_button.click(run_download, inputs=[download_method, download_source, model_to_download],
                          outputs=[download_output], api_name="download_model")

    # Save / reset separation settings across all tabs
    index = [(tab.section, key, comp) for tab in separation_tabs for key, comp in tab.settings.items()]
    all_inputs = [comp for _, _, comp in index]

    def save_settings(*values):
        data = {}
        for (section, key, _), value in zip(index, values):
            data.setdefault(section, {})[key] = value
        try:
            ctx.settings.save_custom(data)
        except OSError as e:
            logger.exception("Error saving settings")
            raise gr.Error(f"{i18n('Error saving settings')}: {e}")
        gr.Info(i18n("Current settings saved successfully! They will be loaded next time"))

    def reset_settings():
        try:
            defaults = ctx.settings.reset()
        except (OSError, ValueError) as e:
            logger.exception("Error resetting settings")
            gr.Warning(i18n("Error resetting settings"))
            return [gr.update() for _ in index]

        updates = []
        for section, key, comp in index:
            value = defaults.get(section, {}).get(key)
            if key == "output_format" and value is None:
                value = DEFAULT_OUTPUT_FORMAT
            if isinstance(comp, gr.Dropdown) and value is not None:
                choices = _choice_values(comp)
                if isinstance(value, list):  # multiselect
                    value = [v for v in value if v in choices]
                elif value not in choices:
                    value = None
            updates.append(gr.update(value=value))
        gr.Info(i18n("Settings reset to default. Default settings will be loaded next time"))
        return updates

    save_button.click(save_settings, inputs=all_inputs, api_visibility="undocumented")
    reset_button.click(reset_settings, outputs=all_inputs, api_visibility="undocumented")

    # Performance
    for component, key, convert in (
        (precision, "performance.precision", str),
        (torch_compile, "performance.torch_compile", bool),
        (chunk_duration, "performance.chunk_duration", lambda v: max(int(v or 0), 0)),
        (use_soundfile, "performance.use_soundfile", bool),
    ):
        component.change(lambda value, key=key, convert=convert: ctx.config.set(key, convert(value)),
                         inputs=[component], api_visibility="undocumented")

    def save_name_template(template):
        template = (template or "").strip() or DEFAULT_NAME_TEMPLATE
        try:
            check_name_template(template)
        except ValueError as e:
            raise gr.Error(f"{i18n('Invalid name template')}: {e}")
        ctx.config.set("output.name_template", template)
        gr.Info(i18n("Name template saved"))
        return template

    name_template.submit(save_name_template, inputs=[name_template], outputs=[name_template],
                         api_visibility="undocumented")

    # Discord
    def save_discord(enabled):
        ctx.config.set("discord_presence", bool(enabled))

    discord_presence.change(save_discord, inputs=[discord_presence], api_visibility="undocumented")


def _current_language(ctx: AppContext) -> str:
    language = normalize_language(ctx.config.get("lang.selected_lang"))
    if not ctx.config.get("lang.override", False) or language not in i18n.available_languages():
        return AUTO_LANGUAGE
    return language


def _choice_values(dropdown: gr.Dropdown) -> list:
    # Gradio stores choices as (label, value) tuples
    return [c[1] if isinstance(c, tuple) else c for c in dropdown.choices]
