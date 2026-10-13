"""Declarative description of each separation architecture.

One ``ArchSpec`` drives both the generic separation service (which kwargs to pass
to ``audio_separator.separator.Separator``) and the generic Gradio tab (which
widgets to render, in which row). Adding a parameter means adding a ``ParamSpec``.

Labels are marked with ``N_`` and translated at render time. They are i18n keys:
do not change their text (that would orphan every translation).
"""

from dataclasses import dataclass
from typing import Any, Literal

from uvr5_ui.i18n import N_


@dataclass(frozen=True)
class ParamSpec:
    key: str  # key in default_settings.json / custom_settings.json
    widget: Literal["slider", "checkbox", "textbox"]
    label: str
    default: Any
    info: str | None = None
    placeholder: str | None = None
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    row: int = 0  # row inside the "Advanced settings" accordion
    visible: bool = True  # hidden params are still saved and passed to Separator
    separator_key: str | None = None  # key inside the arch's params dict (e.g. vr_params)
    common_kwarg: str | None = None  # top-level Separator kwarg (e.g. normalization_threshold)


@dataclass(frozen=True)
class ArchSpec:
    id: str
    tab_label: str
    settings_section: str  # section in default_settings.json; never rename (user files depend on it)
    params_group: str  # Separator kwarg holding the arch-specific dict
    params: tuple[ParamSpec, ...]
    supports_single_stem: bool = True
    show_model_filter: bool = True  # "All models" / "Downloaded models only" buttons

    def param(self, key: str) -> ParamSpec:
        return next(p for p in self.params if p.key == key)

    def defaults(self) -> dict:
        return {p.key: p.default for p in self.params}


def _segment_size(row: int, default: int = 256) -> ParamSpec:
    return ParamSpec(
        "segment_size", "slider", N_("Segment size"), default,
        info=N_("Larger consumes more resources, but may give better results"),
        minimum=32, maximum=4000, step=32, row=row, separator_key="segment_size",
    )


def _batch_size(row: int) -> ParamSpec:
    return ParamSpec(
        "batch_size", "slider", N_("Batch size"), 1,
        info=N_("Larger consumes more RAM but may process slightly faster"),
        minimum=1, maximum=16, step=1, row=row, separator_key="batch_size",
    )


def _thresholds(row: int) -> tuple[ParamSpec, ParamSpec]:
    return (
        ParamSpec(
            "normalization_threshold", "slider", N_("Normalization threshold"), 0.9,
            info=N_("The threshold for audio normalization"),
            minimum=0.1, maximum=1, step=0.1, row=row, common_kwarg="normalization_threshold",
        ),
        ParamSpec(
            "amplification_threshold", "slider", N_("Amplification threshold"), 0.7,
            info=N_("The threshold for audio amplification"),
            minimum=0.1, maximum=1, step=0.1, row=row, common_kwarg="amplification_threshold",
        ),
    )


def _single_stem(row: int) -> ParamSpec:
    return ParamSpec(
        "single_stem", "textbox", N_("Output only single stem"), "",
        placeholder=N_("Write the stem you want, check the stems of each model on Leaderboard. e.g. Instrumental"),
        row=row, common_kwarg="output_single_stem",
    )


def _mdxc_params(overlap_max: int) -> tuple[ParamSpec, ...]:
    return (
        _segment_size(row=0),
        ParamSpec(
            "override_segment_size", "checkbox", N_("Override segment size"), False,
            info=N_("Override model default segment size instead of using the model default value"),
            row=0, separator_key="override_model_segment_size",
        ),
        ParamSpec(
            "overlap", "slider", N_("Overlap"), 8,
            info=N_("Amount of overlap between prediction windows"),
            minimum=2, maximum=overlap_max, step=1, row=1, separator_key="overlap",
        ),
        _batch_size(row=1),
        *_thresholds(row=2),
        _single_stem(row=3),
    )


ROFORMER = ArchSpec(
    id="roformer",
    tab_label="BS/Mel Roformer",
    settings_section="Roformer",
    params_group="mdxc_params",
    params=_mdxc_params(overlap_max=10),
)

MDX23C = ArchSpec(
    id="mdx23c",
    tab_label="MDX23C",
    settings_section="MDX23C",
    params_group="mdxc_params",
    params=_mdxc_params(overlap_max=50),
)

MDXNET = ArchSpec(
    id="mdxnet",
    tab_label="MDX-NET",
    settings_section="MDX-NET",
    params_group="mdx_params",
    params=(
        ParamSpec(
            "hop_length", "slider", N_("Hop length"), 1024,
            info=N_("Usually called stride in neural networks; only change if you know what you're doing"),
            minimum=32, maximum=2048, step=32, row=0, separator_key="hop_length",
        ),
        _segment_size(row=0),
        ParamSpec(
            "denoise", "checkbox", N_("Denoise"), True,
            info=N_("Enable denoising during separation"),
            row=0, separator_key="enable_denoise",
        ),
        ParamSpec(
            "overlap", "slider", N_("Overlap"), 0.25,
            info=N_("Amount of overlap between prediction windows"),
            minimum=0.001, maximum=0.999, step=0.001, row=1, separator_key="overlap",
        ),
        _batch_size(row=1),
        *_thresholds(row=2),
        _single_stem(row=3),
    ),
)

VRARCH = ArchSpec(
    id="vrarch",
    tab_label="VR ARCH",
    settings_section="VR Arch",
    params_group="vr_params",
    params=(
        ParamSpec(
            "window_size", "slider", N_("Window size"), 512,
            info=N_("Balance quality and speed. 1024 = fast but lower, 320 = slower but better quality"),
            minimum=320, maximum=1024, step=32, row=0, separator_key="window_size",
        ),
        ParamSpec(
            "aggression", "slider", N_("Agression"), 5,
            info=N_("Intensity of primary stem extraction"),
            minimum=1, maximum=50, step=1, row=0, separator_key="aggression",
        ),
        ParamSpec(
            "tta", "checkbox", N_("TTA"), True,
            info=N_("Enable Test-Time-Augmentation; slow but improves quality"),
            row=0, separator_key="enable_tta",
        ),
        ParamSpec(
            "post_process", "checkbox", N_("Post process"), False,
            info=N_("Identify leftover artifacts within vocal output; may improve separation for some songs"),
            row=1, separator_key="enable_post_process",
        ),
        ParamSpec(
            "post_process_threshold", "slider", N_("Post process threshold"), 0.2,
            info=N_("Threshold for post-processing"),
            minimum=0.1, maximum=0.3, step=0.1, row=1, separator_key="post_process_threshold",
        ),
        ParamSpec(
            "high_end_process", "checkbox", N_("High end process"), False,
            info=N_("Mirror the missing frequency range of the output"),
            row=2, separator_key="high_end_process",
        ),
        _batch_size(row=2),
        *_thresholds(row=3),
        _single_stem(row=4),
    ),
)

DEMUCS = ArchSpec(
    id="demucs",
    tab_label="Demucs",
    settings_section="Demucs",
    params_group="demucs_params",
    supports_single_stem=False,
    show_model_filter=False,
    params=(
        ParamSpec(
            "shifts", "slider", N_("Shifts"), 2,
            info=N_("Number of predictions with random shifts, higher = slower but better quality"),
            minimum=1, maximum=20, step=1, row=0, separator_key="shifts",
        ),
        ParamSpec(
            "segment_size", "slider", N_("Segment size"), 40,
            info=N_("Size of segments into which the audio is split. Higher = slower but better quality"),
            minimum=1, maximum=100, step=1, row=0, separator_key="segment_size",
        ),
        ParamSpec(
            "segments_enabled", "checkbox", N_("Segment-wise processing"), True,
            info=N_("Enable segment-wise processing"),
            row=0, separator_key="segments_enabled",
        ),
        ParamSpec(
            "overlap", "slider", N_("Overlap"), 0.25,
            info=N_("Overlap between prediction windows. Higher = slower but better quality"),
            minimum=0.001, maximum=0.999, step=0.001, row=1, separator_key="overlap",
        ),
        _batch_size(row=1),
        *_thresholds(row=2),
    ),
)

# Tab order in the UI
ARCHITECTURES: tuple[ArchSpec, ...] = (ROFORMER, MDX23C, MDXNET, VRARCH, DEMUCS)
ARCHITECTURES_BY_ID = {spec.id: spec for spec in ARCHITECTURES}


def build_separator_kwargs(spec: ArchSpec, values: dict) -> dict:
    """Map UI/settings values (keyed by ``ParamSpec.key``) to ``Separator(...)`` kwargs."""
    group = {}
    kwargs = {}
    for param in spec.params:
        value = values.get(param.key, param.default)
        if param.key == "single_stem":
            value = (value or "").strip() or None
        if param.separator_key:
            group[param.separator_key] = value
        if param.common_kwarg:
            kwargs[param.common_kwarg] = value
    kwargs[spec.params_group] = group
    return kwargs
