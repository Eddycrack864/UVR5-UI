"""UI smoke tests: build the Blocks app without launching it and drive handlers directly."""

import json

import pytest

gr = pytest.importorskip("gradio")

from uvr5_ui import paths  # noqa: E402
from uvr5_ui.config.settings import SeparationSettings  # noqa: E402
from uvr5_ui.config.store import ConfigStore  # noqa: E402
from uvr5_ui.core.models.catalog import ModelCatalog  # noqa: E402
from uvr5_ui.core.separation import ensemble, runtime  # noqa: E402
from uvr5_ui.core.separation.ensemble_presets import PresetStore  # noqa: E402
from uvr5_ui.core.separation.runtime import separator_cache  # noqa: E402
from uvr5_ui.ui.app import create_app  # noqa: E402
from uvr5_ui.ui.context import AppContext  # noqa: E402
from tests.test_ensemble import WavSeparator  # noqa: E402
from tests.test_separation import FakeSeparator  # noqa: E402

ENSEMBLE_MODELS = ["UVR-MDX-NET-Inst_HQ_3.onnx", "model_bs_roformer_ep_317_sdr_12.9755.ckpt"]


class NoProgress:
    def __call__(self, *args, **kwargs):
        pass


@pytest.fixture
def ctx(tmp_root, monkeypatch):
    monkeypatch.setattr(runtime, "use_autocast", lambda: False)
    monkeypatch.setattr(runtime, "_separator_class", lambda: FakeSeparator)
    separator_cache.clear()
    FakeSeparator.instances.clear()
    config = ConfigStore(tmp_root / "assets" / "config.default.json", tmp_root / "user_data" / "config.json")
    config.set("theme.class", None)  # avoid fetching a Hub theme
    settings = SeparationSettings(config, tmp_root / "assets" / "default_settings.json",
                                  tmp_root / "user_data" / "custom_settings.json")
    return AppContext(config, settings, ModelCatalog.from_file(tmp_root / "assets" / "models.json"),
                      settings.initial(), PresetStore(tmp_root / "user_data" / "ensemble_presets.json"))


@pytest.fixture
def app(ctx):
    return create_app(ctx)


def find_fn(app, name, nth=0):
    fns = [f for f in app.fns.values() if getattr(f, "name", None) == name or getattr(f, "api_name", None) == name]
    return fns[nth]


def test_tabs(app):
    labels = [b.label for b in app.blocks.values() if type(b).__name__ == "Tab"]
    assert labels == ["BS/Mel Roformer", "MDX23C", "MDX-NET", "VR ARCH", "Demucs", "Ensemble",
                      "Leaderboard", "Themes", "Settings", "Credits"]


def test_telemetry_disabled(app):
    assert app.analytics_enabled is False


def test_single_separation_shows_only_produced_stems(app):
    fn = find_fn(app, "run_single", nth=2)  # MDX-NET tab
    data = {}
    for comp in fn.inputs:
        if isinstance(comp, gr.Dropdown) and comp.label == "Select the model":
            data[comp] = "UVR-MDX-NET-Inst_HQ_3.onnx"
        elif isinstance(comp, gr.Audio):
            data[comp] = "song.wav"
        else:
            data[comp] = comp.value
    updates = fn.fn(data, NoProgress())

    assert len(updates) == 6
    assert updates[0]["visible"] and updates[0]["label"] == "Stem 1 (Vocals)"
    assert updates[1]["label"] == "Stem 2 (Instrumental)"
    assert [u["visible"] for u in updates[2:]] == [False] * 4
    assert FakeSeparator.instances[0].kwargs["mdx_params"]["hop_length"] == 1024


def test_single_separation_requires_model(app):
    fn = find_fn(app, "run_single")
    data = {comp: None for comp in fn.inputs}
    with pytest.raises(gr.Error):
        fn.fn(data, NoProgress())


def test_save_and_reset_settings(app, ctx, tmp_root):
    save = find_fn(app, "save_settings")
    values = [comp.value for comp in save.inputs]
    keys = [(i, comp) for i, comp in enumerate(save.inputs) if getattr(comp, "label", "") == "Segment size"]
    first_segment_index = keys[0][0]
    values[first_segment_index] = 512
    save.fn(*values)

    custom = json.loads((tmp_root / "user_data" / "custom_settings.json").read_text(encoding="utf-8"))
    assert set(custom) == {"Roformer", "MDX23C", "MDX-NET", "VR Arch", "Demucs", "Ensemble"}
    assert custom["Roformer"]["segment_size"] == 512
    assert ctx.config.get("load_custom_settings") is True
    assert ctx.settings.initial()["Roformer"]["segment_size"] == 512

    reset = find_fn(app, "reset_settings")
    updates = reset.fn()
    assert len(updates) == len(save.inputs)
    assert updates[first_segment_index]["value"] == 256
    assert ctx.config.get("load_custom_settings") is False


def by_label(fn, label, cls=None):
    return next(c for c in fn.inputs if getattr(c, "label", None) == label and (cls is None or isinstance(c, cls)))


@pytest.fixture
def wav_separator(tmp_root, monkeypatch):
    monkeypatch.setattr(runtime, "_separator_class", lambda: WavSeparator)
    monkeypatch.setattr(paths, "OUTPUTS_DIR", tmp_root / "outputs")
    monkeypatch.setattr(ensemble, "default_work_dir", lambda: tmp_root / "work")
    WavSeparator.instances.clear()


def test_ensemble_runs_each_model_with_its_tab_settings(app, tmp_root, wav_separator):
    fn = find_fn(app, "separate_ensemble")
    audio = tmp_root / "song.wav"
    audio.touch()
    data = {comp: comp.value for comp in fn.inputs}
    data[by_label(fn, "Models")] = ENSEMBLE_MODELS
    data[by_label(fn, "Weights")] = [["UVR-MDX-NET-Inst_HQ_3.onnx", 3], ["BS-Roformer-Viperx-1297", 1]]
    data[by_label(fn, "Input audio")] = str(audio)

    updates = fn.fn(data, NoProgress())

    assert updates[0]["label"] == "Stem 1 (Vocals)"
    assert updates[0]["value"].endswith("song_(Vocals)_ensemble_avg_wave.wav")
    assert [u["visible"] for u in updates[2:]] == [False] * 4
    mdxnet, roformer = WavSeparator.instances
    assert mdxnet.kwargs["mdx_params"]["hop_length"] == 1024
    assert roformer.kwargs["mdxc_params"]["overlap"] == 8
    assert roformer.kwargs["output_single_stem"] is None


def test_ensemble_requires_two_models(app, tmp_root, wav_separator):
    fn = find_fn(app, "separate_ensemble")
    data = {comp: comp.value for comp in fn.inputs}
    data[by_label(fn, "Models")] = ENSEMBLE_MODELS[:1]
    data[by_label(fn, "Input audio")] = "song.wav"
    with pytest.raises(gr.Error, match="at least two models"):
        fn.fn(data, NoProgress())


def test_ensemble_presets(app, ctx):
    apply = find_fn(app, "apply_preset")
    models, algorithm, weights, info = apply.fn("vocal_clean")
    assert models["value"] == ["bs_roformer_vocals_revive_v2_unwa.ckpt", "mel_band_roformer_kim_ft2_bleedless_unwa.ckpt"]
    assert algorithm["value"] == "min_fft"
    assert [row[1] for row in weights["value"]] == [1.0, 1.0]
    assert "Vocal Clean" in info

    save = find_fn(app, "run_save_preset")
    choices, _ = save.fn("Mine", "", ENSEMBLE_MODELS, "avg_wave", [["BS-Roformer-Viperx-1297", 2]])
    assert choices["value"] == "user_mine"
    assert ctx.presets.get("user_mine").weights == (1.0, 2.0)

    delete = find_fn(app, "run_delete_preset")
    with pytest.raises(gr.Error):
        delete.fn("vocal_clean")
    choices, _ = delete.fn("user_mine")
    assert choices["value"] == "custom"
    assert ctx.presets.get("user_mine") is None


def test_performance_settings_reach_the_separator(app, ctx):
    ctx.config.set("performance.precision", "native_fp16")
    ctx.config.set("performance.chunk_duration", 600)
    test_single_separation_shows_only_produced_stems(app)
    kwargs = FakeSeparator.instances[-1].kwargs
    assert kwargs["use_native_fp16"] is True and kwargs["chunk_duration"] == 600


def test_name_template_setting(app, ctx):
    save = find_fn(app, "save_name_template")
    assert save.fn("{stem} - {input}") == "{stem} - {input}"
    assert ctx.config.get("output.name_template") == "{stem} - {input}"
    with pytest.raises(gr.Error):
        save.fn("{input}")
    assert ctx.config.get("output.name_template") == "{stem} - {input}"
    assert save.fn("  ") == "{input}_({stem})_{model}"
