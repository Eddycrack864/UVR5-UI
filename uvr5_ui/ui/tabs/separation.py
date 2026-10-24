"""One generic tab, instantiated once per ``ArchSpec``."""

from dataclasses import dataclass, field
from itertools import groupby

import gradio as gr

from uvr5_ui.core.audio import OUTPUT_FORMATS
from uvr5_ui.core.separation.runtime import RuntimeOptions
from uvr5_ui.core.separation.service import is_folder, separate_batch, separate_file
from uvr5_ui.core.separation.specs import ArchSpec
from uvr5_ui.i18n import N_, i18n
from uvr5_ui.integrations.discord_presence import presence
from uvr5_ui.ui import components, stem_mixer
from uvr5_ui.ui.adapters import GPU_CONCURRENCY_ID, filled, progress_callback, require, user_errors, validations
from uvr5_ui.ui.context import AppContext

DEFAULT_OUTPUT_FORMAT = "wav"
FIRST_USE_MESSAGE = N_(
    "This is the first time the {model} model is being used. "
    "The separation will take a little longer because the model needs to be downloaded."
)


@dataclass
class SeparationTab:
    section: str  # section in default_settings.json / custom_settings.json
    # Persistable inputs keyed like default_settings.json (model, output_format, params..., link, paths)
    settings: dict[str, gr.components.Component] = field(default_factory=dict)
    spec: ArchSpec | None = None  # None for tabs that are not a single architecture (Ensemble)
    params: dict[str, gr.components.Component] = field(default_factory=dict)  # keyed by ParamSpec.key


def render_separation_tab(spec: ArchSpec, ctx: AppContext) -> SeparationTab:
    section = ctx.initial_settings.get(spec.settings_section, {})
    model_ids = ctx.catalog.ids(spec.id)
    initial_model = section.get("model") if section.get("model") in model_ids else None

    with gr.TabItem(spec.tab_label):
        with gr.Row():
            model = gr.Dropdown(label=i18n("Select the model"), value=initial_model, interactive=True,
                                choices=components.model_choices(ctx.catalog, ctx.catalog.by_arch(spec.id)))
            if spec.show_model_filter:
                with gr.Row():
                    with gr.Column():
                        all_models = gr.Button(i18n("All models"), variant="primary")
                        downloaded_models = gr.Button(i18n("Downloaded models only"), variant="primary")
                    output_format = output_format_dropdown(section)
                all_models.click(lambda: _model_choices(ctx, spec, downloaded_only=False), outputs=[model],
                                 api_visibility="undocumented")
                downloaded_models.click(lambda: _model_choices(ctx, spec, downloaded_only=True), outputs=[model],
                                        api_visibility="undocumented")
            else:
                output_format = output_format_dropdown(section)

        params = {}
        with gr.Accordion(i18n("Advanced settings"), open=False):
            with gr.Group():
                for _, row_params in groupby(spec.params, key=lambda p: p.row):
                    with gr.Row():
                        for param in row_params:
                            params[param.key] = components.param_widget(param, section.get(param.key, param.default))

        inputs = components.input_sections(section, spec.id)

        with gr.Row():
            separate_button = gr.Button(i18n("Separate!"), variant="primary")
        stems = components.stem_outputs()
        zip_button = components.zip_download()
        mixer_box, mixer = stem_mixer.stem_mixer()

    # Handlers take named arguments (inputs_kwargs), which are also the API's parameter names:
    # model, output_format, audio / input_path + output_path, and every ParamSpec key.
    fields = {"model": model, "output_format": output_format, **params}

    @user_errors
    def run_single(model, output_format, audio, progress=gr.Progress(track_tqdm=True), **values):
        selected = _selected_model(ctx, spec, model)
        audio_path = require(audio, N_("Please provide an input audio"))
        notify_first_use(ctx, selected)
        with presence.track(spec.id):
            results = separate_file(
                spec, selected, audio_path, output_format or DEFAULT_OUTPUT_FORMAT, values,
                progress=progress_callback(progress), options=RuntimeOptions.from_config(ctx.config),
            )
        return [*components.stem_updates(results), components.zip_update(results, audio_path)]

    def validate_single(model, output_format, audio, **values):
        return validations(
            (fields["model"], filled(model), N_("Please select a model first")),
            (inputs.audio, filled(audio), N_("Please provide an input audio")),
        )

    @user_errors
    def run_batch(model, output_format, input_path, output_path, progress=gr.Progress(), **values):
        selected = _selected_model(ctx, spec, model)
        notify_first_use(ctx, selected)
        lines = []
        with presence.track(spec.id, batch=True):
            for line in separate_batch(
                spec, selected, input_path, output_path, output_format or DEFAULT_OUTPUT_FORMAT, values,
                progress=progress_callback(progress), options=RuntimeOptions.from_config(ctx.config),
            ):
                lines.append(line)
                yield "\n".join(lines)

    def validate_batch(model, output_format, input_path, output_path, **values):
        return validations(
            (fields["model"], filled(model), N_("Please select a model first")),
            (inputs.input_path, is_folder(input_path),
             N_("The input path must be an existing folder")),
        )

    separate_button.click(
        run_single, inputs_kwargs={**fields, "audio": inputs.audio}, outputs=[*stems, zip_button],
        validator=validate_single, api_name=f"separate_{spec.id}",
        concurrency_limit=1, concurrency_id=GPU_CONCURRENCY_ID,
    ).success(  # a separate step, so the API's outputs stay the same
        stem_mixer.mixer_update, inputs=[inputs.audio, *stems], outputs=[mixer_box, mixer],
        api_visibility="undocumented",
    )
    batch_event = inputs.batch_button.click(
        run_batch, inputs_kwargs={**fields, "input_path": inputs.input_path, "output_path": inputs.output_path},
        outputs=[inputs.batch_info], validator=validate_batch, api_name=f"batch_{spec.id}",
        concurrency_limit=1, concurrency_id=GPU_CONCURRENCY_ID,
    )
    inputs.wire_stop(batch_event)

    return SeparationTab(
        section=spec.settings_section,
        settings={
            "model": model,
            "output_format": output_format,
            **params,
            "link": inputs.link,
            "input_path": inputs.input_path,
            "output_path": inputs.output_path,
        },
        spec=spec,
        params=params,
    )


def output_format_dropdown(section: dict):
    return gr.Dropdown(
        label=i18n("Select the output format"),
        choices=OUTPUT_FORMATS,
        value=section.get("output_format") or DEFAULT_OUTPUT_FORMAT,
        interactive=True,
    )


def _model_choices(ctx: AppContext, spec: ArchSpec, downloaded_only: bool):
    models = ctx.catalog.downloaded(spec.id) if downloaded_only else ctx.catalog.by_arch(spec.id)
    return gr.update(choices=components.model_choices(ctx.catalog, models), value=None)


def _selected_model(ctx: AppContext, spec: ArchSpec, model_id):
    require(model_id, N_("Please select a model first"))
    return ctx.catalog.get(spec.id, model_id)


def notify_first_use(ctx: AppContext, model) -> None:
    if not ctx.catalog.is_downloaded(model):
        gr.Info(i18n(FIRST_USE_MESSAGE).format(model=model.id))
