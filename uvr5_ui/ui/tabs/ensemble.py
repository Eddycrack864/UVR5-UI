"""The Ensemble tab: combine the stems of several models, from any architecture."""

import math
from itertools import groupby

import gradio as gr

from uvr5_ui.core.downloads.model_downloader import METHOD_PYTHON, download_model
from uvr5_ui.core.separation.ensemble import (
    ALGORITHMS, DEFAULT_ALGORITHM, MAX_MODELS, WEIGHTED_ALGORITHMS, EnsembleConfigError, EnsembleMember,
    EnsembleOptions, check_ensemble, ensemble_batch, ensemble_file,
)
from uvr5_ui.core.separation.ensemble_presets import EnsemblePreset
from uvr5_ui.core.separation.runtime import RuntimeOptions
from uvr5_ui.core.separation.service import is_folder
from uvr5_ui.core.separation.specs import ARCHITECTURES, ARCHITECTURES_BY_ID, ENSEMBLE_PARAMS, ENSEMBLE_SECTION
from uvr5_ui.i18n import N_, i18n
from uvr5_ui.integrations.discord_presence import presence
from uvr5_ui.ui import a11y, components, stem_mixer
from uvr5_ui.ui.adapters import GPU_CONCURRENCY_ID, filled, progress_callback, require, user_errors, validations
from uvr5_ui.ui.context import AppContext
from uvr5_ui.ui.tabs.separation import DEFAULT_OUTPUT_FORMAT, SeparationTab, output_format_dropdown

CUSTOM_PRESET = "custom"
DEFAULT_WEIGHT = 1.0
FIRST_USE_MESSAGE = N_(
    "Some models are used for the first time ({models}). "
    "The ensemble will take a little longer because they need to be downloaded."
)

# algorithm -> (label, description)
ALGORITHM_INFO = {
    "avg_wave": (N_("Average (waveform)"),
                 N_("Weighted average of the waveforms. A safe default for any combination of models.")),
    "median_wave": (N_("Median (waveform)"),
                    N_("Median of the waveforms: ignores the model that differs the most. Use three or more models (with two it equals the average).")),
    "min_wave": (N_("Minimum (waveform)"),
                 N_("Keeps the quietest sample among the models. Less bleed, thinner sound.")),
    "max_wave": (N_("Maximum (waveform)"),
                 N_("Keeps the loudest sample among the models. Fuller sound, more bleed.")),
    "avg_fft": (N_("Average (spectrogram)"),
                N_("Weighted average of the spectrograms. Smoother than the waveform average.")),
    "median_fft": (N_("Median (spectrogram)"),
                   N_("Median of the spectrograms: ignores the model that differs the most. Use three or more models.")),
    "min_fft": (N_("Minimum (spectrogram)"),
                N_("Keeps the quietest frequency of every moment. The cleanest result, with the least bleed.")),
    "max_fft": (N_("Maximum (spectrogram)"),
                N_("Keeps the loudest frequency of every moment. The fullest result, with more bleed.")),
    "uvr_max_spec": (N_("UVR Max Spec"),
                     N_("Ultimate Vocal Remover's Max Spec. Popular for full instrumentals.")),
    "uvr_min_spec": (N_("UVR Min Spec"),
                     N_("Ultimate Vocal Remover's Min Spec. Popular for clean vocals.")),
    "ensemble_wav": (N_("UVR least noisy chunk"),
                     N_("Ultimate Vocal Remover's chunk ensemble: keeps the least noisy chunk of every model. Experimental.")),
}


def render_ensemble_tab(ctx: AppContext, arch_tabs: list[SeparationTab]) -> SeparationTab:
    section = ctx.initial_settings.get(ENSEMBLE_SECTION, {})
    tabs_by_arch = {tab.spec.id: tab for tab in arch_tabs if tab.spec}
    all_models = [model for spec in ARCHITECTURES for model in ctx.catalog.by_arch(spec.id)]
    model_choices = [
        (components.model_label(ctx.catalog, model, f"{ARCHITECTURES_BY_ID[model.arch].tab_label} · "), model.filename)
        for model in ctx.catalog.recommended_first(all_models)
    ]
    valid_files = {filename for _, filename in model_choices}
    initial_models = [f for f in section.get("models") or [] if f in valid_files]
    initial_algorithm = section.get("algorithm") if section.get("algorithm") in ALGORITHMS else DEFAULT_ALGORITHM
    initial_preset = section.get("preset") if section.get("preset") in _preset_ids(ctx) else CUSTOM_PRESET
    initial_missing = _missing_models(ctx, initial_models)

    with gr.TabItem(i18n("Ensemble")):
        gr.Markdown(i18n("Combine the results of several models into a single, better separation. "
                         "Each model runs with the advanced settings of its own tab."))
        with gr.Row():
            preset = gr.Dropdown(
                label=i18n("Preset"),
                info=i18n("Curated combinations from the community, or your own"),
                choices=_preset_choices(ctx),
                value=initial_preset,
                interactive=True,
            )
            output_format = output_format_dropdown(section)
        preset_info = gr.Markdown(_preset_markdown(ctx, initial_preset))

        models = gr.Dropdown(
            label=i18n("Models"),
            info=i18n("Select between two and six models of any architecture"),
            choices=model_choices,
            value=initial_models,
            multiselect=True,
            max_choices=MAX_MODELS,
            interactive=True,
        )
        with gr.Accordion(i18n("Models not downloaded yet"), open=False, visible=bool(initial_missing)) as missing_box:
            missing_info = gr.Markdown(_missing_markdown(initial_missing))
            download_missing = gr.Button(i18n("Download missing models"), variant="primary")
            download_log = components.output_log()

        with gr.Row():
            algorithm = gr.Dropdown(
                label=i18n("Ensemble algorithm"),
                choices=[(f"{i18n(label)} · {key}", key) for key, (label, _) in ALGORITHM_INFO.items()],
                value=initial_algorithm,
                interactive=True,
            )
        algorithm_info = gr.Markdown(_algorithm_markdown(initial_algorithm))
        weights = gr.Dataframe(
            label=i18n("Weights"),
            headers=[i18n("Model"), i18n("Weight")],
            datatype=["str", "number"],
            type="array",
            static_columns=[0],
            value=_weight_rows(ctx, initial_models, section.get("weights")),
            visible=initial_algorithm in WEIGHTED_ALGORITHMS,
            interactive=True,
        )

        params = {}
        with gr.Accordion(i18n("Advanced settings"), open=False):
            with gr.Group():
                for _, row_params in groupby(ENSEMBLE_PARAMS, key=lambda p: p.row):
                    with gr.Row():
                        for param in row_params:
                            params[param.key] = components.param_widget(param, section.get(param.key, param.default))

        with gr.Accordion(i18n("Manage presets"), open=False):
            with gr.Row():
                preset_name = components.single_line_textbox(i18n("Preset name"), i18n("Name of the new preset"))
                preset_description = components.single_line_textbox(i18n("Description"), i18n("Optional"))
            with gr.Row():
                save_preset = gr.Button(i18n("Save as preset"), variant="primary")
                delete_preset = gr.Button(i18n("Delete selected preset"), variant="stop")

        inputs = components.input_sections(section, "ensemble")

        with gr.Row():
            separate_button = gr.Button(i18n("Separate!"), variant="primary")
        stems = components.stem_outputs()
        zip_button = components.zip_download()
        mixer_box, mixer = stem_mixer.stem_mixer()
        announcer = a11y.announcer()

    # Presets, models, algorithm and weights
    def apply_preset(preset_id):
        found = ctx.presets.get(preset_id)
        if found is None:
            return gr.update(), gr.update(), gr.update(), _preset_markdown(ctx, preset_id)
        files = [f for f in found.models if f in valid_files]
        return (
            gr.update(value=files),
            gr.update(value=found.algorithm),
            gr.update(value=_weight_rows(ctx, files, found.weights)),
            _preset_markdown(ctx, preset_id),
        )

    def models_edited(files, rows):
        # Keep the weights already typed for models that are still selected
        typed = {str(row[0]): row[1] for row in rows or [] if len(row) >= 2 and row[0]}
        new_rows = [[_model_id(ctx, f), typed.get(_model_id(ctx, f), DEFAULT_WEIGHT)] for f in files or []]
        return gr.update(value=new_rows), CUSTOM_PRESET, ""

    def models_changed(files):
        missing = _missing_models(ctx, files or [])
        return gr.update(visible=bool(missing)), _missing_markdown(missing)

    def algorithm_changed(name):
        return gr.update(visible=name in WEIGHTED_ALGORITHMS), _algorithm_markdown(name)

    preset.input(apply_preset, inputs=[preset], outputs=[models, algorithm, weights, preset_info],
                 api_visibility="undocumented")
    models.input(models_edited, inputs=[models, weights], outputs=[weights, preset, preset_info],
                 api_visibility="undocumented")
    models.change(models_changed, inputs=[models], outputs=[missing_box, missing_info], api_visibility="undocumented")
    algorithm.input(lambda: (CUSTOM_PRESET, ""), outputs=[preset, preset_info], api_visibility="undocumented")
    algorithm.change(algorithm_changed, inputs=[algorithm], outputs=[weights, algorithm_info],
                     api_visibility="undocumented")

    @user_errors
    def run_download(files, progress=gr.Progress()):
        lines = []
        for model in _missing_models(ctx, files or []):
            for line in download_model(model, "Github", METHOD_PYTHON, progress=progress_callback(progress)):
                lines.append(line)
                yield "\n".join(lines), gr.update()
        missing = _missing_models(ctx, files or [])
        yield "\n".join(lines), _missing_markdown(missing)

    download_missing.click(run_download, inputs=[models], outputs=[download_log, missing_info],
                           api_visibility="undocumented")

    @user_errors
    def run_save_preset(name, description, files, algorithm_name, rows):
        require(name, N_("Please write a name for the preset"))
        saved = ctx.presets.save(name, files or [], algorithm_name, _weights(ctx, files or [], rows, algorithm_name),
                                 description or "")
        gr.Info(i18n("Preset saved"))
        return gr.update(choices=_preset_choices(ctx), value=saved.id), _preset_markdown(ctx, saved.id)

    @user_errors
    def run_delete_preset(preset_id):
        if not ctx.presets.delete(preset_id or ""):
            raise gr.Error(i18n("Only your own presets can be deleted"))
        gr.Info(i18n("Preset deleted"))
        return gr.update(choices=_preset_choices(ctx), value=CUSTOM_PRESET), ""

    save_preset.click(run_save_preset, inputs=[preset_name, preset_description, models, algorithm, weights],
                      outputs=[preset, preset_info], api_visibility="undocumented")
    delete_preset.click(run_delete_preset, inputs=[preset], outputs=[preset, preset_info],
                        api_visibility="undocumented")

    # Separation. Handlers take named arguments (inputs_kwargs), which are also the API's
    # parameter names. Each architecture's params are prefixed with its id (roformer_overlap...).
    fields = {"preset": preset, "models": models, "algorithm": algorithm, "weights": weights,
              "output_format": output_format, **params}
    arch_fields = {f"{tab.spec.id}_{key}": comp for tab in arch_tabs for key, comp in tab.params.items()}

    def members_and_options(files, algorithm_name, rows, preset_id, values):
        files = files or []
        algorithm_name = algorithm_name or DEFAULT_ALGORITHM
        members = []
        for filename in files:
            model = ctx.catalog.by_filename(filename)
            if model is None:
                raise gr.Error(f"{i18n('Unknown model')}: {filename}")
            tab = tabs_by_arch[model.arch]
            members.append(EnsembleMember(ARCHITECTURES_BY_ID[model.arch], model,
                                          {key: values[f"{model.arch}_{key}"] for key in tab.params}))
        options = EnsembleOptions(
            algorithm=algorithm_name,
            weights=_weights(ctx, files, rows, algorithm_name),
            name=_ensemble_name(ctx, preset_id, files, algorithm_name),
            include_unmatched=bool(values["include_unmatched"]),
            keep_intermediates=bool(values["keep_intermediates"]),
            normalization_threshold=values["normalization_threshold"],
            amplification_threshold=values["amplification_threshold"],
        )
        missing = [m.id for m in _missing_models(ctx, files)]
        if missing:
            gr.Info(i18n(FIRST_USE_MESSAGE).format(models=", ".join(missing)))
        return members, options

    def ensemble_checks(files, algorithm_name, rows) -> list:
        files = files or []
        algorithm_name = algorithm_name or DEFAULT_ALGORITHM
        try:
            check_ensemble(len(files), algorithm_name, _weights(ctx, files, rows, algorithm_name))
        except EnsembleConfigError as e:
            component = {"models": fields["models"], "algorithm": fields["algorithm"]}.get(e.field, fields["weights"])
            return [(component, False, e.message)]
        return []

    @user_errors
    def run_single(models, algorithm, weights, preset, output_format, audio, progress=gr.Progress(track_tqdm=True),
                   **values):
        audio_path = require(audio, N_("Please provide an input audio"))
        members, options = members_and_options(models, algorithm, weights, preset, values)
        with presence.track("ensemble"):
            results = ensemble_file(members, audio_path, output_format or DEFAULT_OUTPUT_FORMAT, options,
                                    progress=progress_callback(progress),
                                    runtime_options=RuntimeOptions.from_config(ctx.config))
        return [*components.stem_updates(results), components.zip_update(results, audio_path)]

    def validate_single(models, algorithm, weights, preset, output_format, audio, **values):
        return validations(*ensemble_checks(models, algorithm, weights),
                           (inputs.audio, filled(audio), N_("Please provide an input audio")))

    @user_errors
    def run_batch(models, algorithm, weights, preset, output_format, input_path, output_path,
                  progress=gr.Progress(), **values):
        members, options = members_and_options(models, algorithm, weights, preset, values)
        lines = []
        with presence.track("ensemble", batch=True):
            for line in ensemble_batch(members, input_path, output_path, output_format or DEFAULT_OUTPUT_FORMAT,
                                       options, progress=progress_callback(progress),
                                       runtime_options=RuntimeOptions.from_config(ctx.config)):
                lines.append(line)
                yield "\n".join(lines)

    def validate_batch(models, algorithm, weights, preset, output_format, input_path, output_path, **values):
        return validations(*ensemble_checks(models, algorithm, weights),
                           (inputs.input_path, is_folder(input_path),
                            N_("The input path must be an existing folder")))

    separate_event = separate_button.click(
        run_single, inputs_kwargs={**fields, **arch_fields, "audio": inputs.audio}, outputs=[*stems, zip_button],
        validator=validate_single, api_name="separate_ensemble",
        concurrency_limit=1, concurrency_id=GPU_CONCURRENCY_ID,
    )
    # Separate steps, so the API's outputs stay the same. No progress of their own, so screen
    # readers hear "Complete" once
    separate_event.success(stem_mixer.mixer_update, inputs=[inputs.audio, *stems], outputs=[mixer_box, mixer],
                           show_progress="hidden", api_visibility="undocumented")
    separate_event.success(a11y.announce_stems, inputs=stems, outputs=announcer, show_progress="hidden",
                           api_visibility="undocumented")
    batch_event = inputs.batch_button.click(
        run_batch,
        inputs_kwargs={**fields, **arch_fields, "input_path": inputs.input_path, "output_path": inputs.output_path},
        outputs=[inputs.batch_info], validator=validate_batch, api_name="batch_ensemble",
        concurrency_limit=1, concurrency_id=GPU_CONCURRENCY_ID,
    )
    batch_event.success(a11y.announce_batch, inputs=inputs.batch_info, outputs=announcer,
                        show_progress="hidden", api_visibility="undocumented")
    inputs.wire_stop(batch_event)

    return SeparationTab(
        section=ENSEMBLE_SECTION,
        settings={
            "preset": preset,
            "models": models,
            "algorithm": algorithm,
            "weights": weights,
            "output_format": output_format,
            **params,
            "link": inputs.link,
            "input_path": inputs.input_path,
            "output_path": inputs.output_path,
        },
        params=params,
    )


def _usable_presets(ctx: AppContext) -> list[EnsemblePreset]:
    """Presets whose models are all in the catalog."""
    return [p for p in ctx.presets.all() if all(ctx.catalog.by_filename(f) for f in p.models)]


def _preset_ids(ctx: AppContext) -> set[str]:
    return {p.id for p in _usable_presets(ctx)}


def _preset_choices(ctx: AppContext) -> list[tuple[str, str]]:
    choices = [(i18n("Custom"), CUSTOM_PRESET)]
    for p in _usable_presets(ctx):
        choices.append((f"★ {p.name}" if p.is_user else p.name, p.id))
    return choices


def _preset_markdown(ctx: AppContext, preset_id: str | None) -> str:
    found = ctx.presets.get(preset_id) if preset_id and preset_id != CUSTOM_PRESET else None
    if found is None:
        return ""
    models = ", ".join(_model_id(ctx, f) for f in found.models)
    lines = [f"**{found.name}**" + (f": {found.description}" if found.description else ""),
             f"{i18n('Models')}: {models}",
             f"{i18n('Ensemble algorithm')}: `{found.algorithm}`"]
    if found.contributor:
        lines.append(f"{i18n('Contributor')}: {found.contributor}")
    return "\n\n".join(lines)


def _algorithm_markdown(name: str) -> str:
    label, description = ALGORITHM_INFO.get(name, ("", ""))
    return f"*{i18n(description)}*" if description else ""


def _model_id(ctx: AppContext, filename: str) -> str:
    model = ctx.catalog.by_filename(filename)
    return model.id if model else filename


def _missing_models(ctx: AppContext, files) -> list:
    models = [ctx.catalog.by_filename(f) for f in files]
    return [m for m in models if m is not None and not ctx.catalog.is_downloaded(m)]


def _missing_markdown(missing) -> str:
    if not missing:
        return i18n("All the selected models are downloaded")
    names = "\n".join(f"- {m.id}" for m in missing)
    return (f"{i18n('These models will be downloaded the first time they are used, or you can download them now')}:"
            f"\n\n{names}")


def _weight_rows(ctx: AppContext, files, weights) -> list[list]:
    """Rows of the weights table. ``weights`` is a list of numbers or of saved ``[model, weight]`` rows."""
    if weights and all(isinstance(row, (list, tuple)) for row in weights):
        typed = {str(row[0]): row[1] for row in weights if len(row) >= 2}
        values = [typed.get(_model_id(ctx, f), DEFAULT_WEIGHT) for f in files]
    elif weights and len(weights) == len(files):
        values = list(weights)
    else:
        values = [DEFAULT_WEIGHT] * len(files)
    return [[_model_id(ctx, f), w] for f, w in zip(files, values)]


def _weights(ctx: AppContext, files, rows, algorithm_name: str) -> tuple[float, ...] | None:
    """One weight per selected model, read from the table by model name (missing rows weigh 1)."""
    if algorithm_name not in WEIGHTED_ALGORITHMS:
        return None
    typed = {}
    for row in rows or []:
        if len(row) >= 2 and row[0]:
            try:
                typed[str(row[0])] = float(row[1])
            except (TypeError, ValueError):
                typed[str(row[0])] = math.nan  # rejected by check_ensemble
    return tuple(typed.get(_model_id(ctx, f), DEFAULT_WEIGHT) for f in files)


def _ensemble_name(ctx: AppContext, preset_id, files, algorithm_name: str) -> str | None:
    """The preset id for output filenames, if the selection still is that preset."""
    found = ctx.presets.get(preset_id) if preset_id and preset_id != CUSTOM_PRESET else None
    if found and list(found.models) == list(files) and found.algorithm == algorithm_name:
        return found.id
    return None
