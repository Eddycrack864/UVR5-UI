"""UI smoke tests: build the Blocks app without launching it and drive handlers directly."""

import json
import zipfile

import numpy as np
import pytest
import soundfile as sf

gr = pytest.importorskip("gradio")

from uvr5_ui import paths  # noqa: E402
from uvr5_ui.config.settings import SeparationSettings  # noqa: E402
from uvr5_ui.config.store import ConfigStore  # noqa: E402
from uvr5_ui.core.models.catalog import ModelCatalog  # noqa: E402
from uvr5_ui.core.separation import ensemble, runtime  # noqa: E402
from uvr5_ui.core.separation.ensemble_presets import PresetStore  # noqa: E402
from uvr5_ui.core.separation.runtime import separator_cache  # noqa: E402
from uvr5_ui.ui.app import create_app  # noqa: E402
from uvr5_ui.ui.components import model_choices  # noqa: E402
from uvr5_ui.ui import a11y  # noqa: E402
from uvr5_ui.ui.app import launch_kwargs  # noqa: E402
from uvr5_ui.ui.tabs.separation import _model_choices  # noqa: E402
from uvr5_ui.core.separation.specs import ARCHITECTURES_BY_ID as SPECS  # noqa: E402
from uvr5_ui.ui.stem_mixer import mixer_update, mixer_value  # noqa: E402
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


def kwargs_of(fn, **overrides):
    """Every input of an inputs_kwargs event at its initial value, by parameter name."""
    values = {name: comp.value for name, comp in zip(fn.input_keyword_names, fn.inputs)}
    values.update(overrides)
    return values


def invalid(result: dict) -> dict:
    """{component label: message} for the failed checks of a validator."""
    return {comp.label: v["message"] for comp, v in result.items() if not v["is_valid"]}


def test_tabs(app):
    labels = [b.label for b in app.blocks.values() if type(b).__name__ == "Tab"]
    assert labels == ["BS/Mel Roformer", "MDX23C", "MDX-NET", "VR ARCH", "Demucs", "Ensemble",
                      "Leaderboard", "Themes", "Settings", "Credits"]


def test_telemetry_disabled(app):
    assert app.analytics_enabled is False


def test_single_separation_shows_only_produced_stems(app):
    fn = find_fn(app, "separate_mdxnet")
    assert fn.input_keyword_names[:3] == ["model", "output_format", "hop_length"]
    updates = fn.fn(**kwargs_of(fn, model="UVR-MDX-NET-Inst_HQ_3.onnx", audio="song.wav"), progress=NoProgress())

    assert len(updates) == 7
    assert updates[6]["visible"] is False  # FakeSeparator writes no files: nothing to zip
    assert updates[0]["visible"] and updates[0]["label"] == "Stem 1 (Vocals)"
    assert updates[1]["label"] == "Stem 2 (Instrumental)"
    assert [u["visible"] for u in updates[2:6]] == [False] * 4
    assert FakeSeparator.instances[0].kwargs["mdx_params"]["hop_length"] == 1024


def test_single_separation_requires_model(app):
    fn = find_fn(app, "separate_roformer")
    with pytest.raises(gr.Error):
        fn.fn(**kwargs_of(fn, audio="song.wav"), progress=NoProgress())
    assert invalid(fn.validator(**kwargs_of(fn))) == {
        "Select the model": "Please select a model first", "Input audio": "Please provide an input audio"}
    assert invalid(fn.validator(**kwargs_of(fn, model="BS-Roformer-Viperx-1297", audio="song.wav"))) == {}


def test_batch_validator(app, tmp_path):
    fn = find_fn(app, "batch_vrarch")
    assert invalid(fn.validator(**kwargs_of(fn, model="1_HP-UVR.pth", input_path=str(tmp_path / "missing")))) == {
        "Input path": "The input path must be an existing folder"}
    assert invalid(fn.validator(**kwargs_of(fn, model="1_HP-UVR.pth", input_path=str(tmp_path)))) == {}


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
    kwargs = kwargs_of(fn, models=ENSEMBLE_MODELS, audio=str(audio),
                       weights=[["UVR-MDX-NET-Inst_HQ_3.onnx", 3], ["BS-Roformer-Viperx-1297", 1]])
    assert kwargs["roformer_overlap"] == 8 and "mdxnet_hop_length" in kwargs

    updates = fn.fn(**kwargs, progress=NoProgress())

    assert updates[0]["label"] == "Stem 1 (Vocals)"
    assert updates[0]["value"].endswith("song_(Vocals)_ensemble_avg_wave.wav")
    assert [u["visible"] for u in updates[2:6]] == [False] * 4
    assert updates[6]["visible"] and updates[6]["value"].endswith("song_stems.zip")
    with zipfile.ZipFile(updates[6]["value"]) as archive:
        assert sorted(archive.namelist()) == ["song_(Instrumental)_ensemble_avg_wave.wav",
                                              "song_(Vocals)_ensemble_avg_wave.wav"]
    mdxnet, roformer = WavSeparator.instances
    assert mdxnet.kwargs["mdx_params"]["hop_length"] == 1024
    assert roformer.kwargs["mdxc_params"]["overlap"] == 8
    assert roformer.kwargs["output_single_stem"] is None


def test_ensemble_requires_two_models(app, tmp_root, wav_separator):
    fn = find_fn(app, "separate_ensemble")
    kwargs = kwargs_of(fn, models=ENSEMBLE_MODELS[:1], audio="song.wav", weights=[])
    with pytest.raises(gr.Error, match="at least two models"):
        fn.fn(**kwargs, progress=NoProgress())
    assert invalid(fn.validator(**kwargs)) == {"Models": "Select at least two models for the ensemble"}
    bad_weights = kwargs_of(fn, models=ENSEMBLE_MODELS, audio="song.wav", weights=[["BS-Roformer-Viperx-1297", -1]])
    assert invalid(fn.validator(**bad_weights)) == {
        "Weights": "Weights must be non-negative numbers that add up to more than zero"}
    assert invalid(fn.validator(**kwargs_of(fn, models=ENSEMBLE_MODELS, audio="song.wav", weights=[]))) == {}


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


def test_temp_cache_is_cleaned(app):
    assert app.delete_cache == (86400, 86400)


def test_batch_can_be_stopped(app):
    batch = find_fn(app, "batch_mdxnet")
    cancellers = [f for f in app.fns.values() if f.fn is None and batch._id in (f.cancels or [])]
    assert len(cancellers) == 1


def test_recommended_models_come_first_with_their_stem(ctx):
    choices = model_choices(ctx.catalog, ctx.catalog.by_arch("roformer"))
    assert choices[:2] == [
        ("BS Roformer | Instrumental Resurrection by unwa (Instrumental ⭐)",
         "BS Roformer | Instrumental Resurrection by unwa"),
        ("BS Roformer SW by jarredou (Vocals ⭐)", "BS Roformer SW by jarredou"),
    ]
    # The values stay the model ids, so saved settings and the API are unchanged
    assert sorted(value for _, value in choices) == sorted(ctx.catalog.ids("roformer"))
    assert sum("⭐" in label for label, _ in choices) == 5


def test_mixer_value():
    paths = ["/c/song_(Vocals)_m.wav", None, "/c/song_(Instrumental)_m.flac", "/c/custom_name.wav", None, None]
    value = mixer_value("/tmp/My Song.mp3", paths)
    assert value["name"] == "My Song_mix"
    assert [s["label"] for s in value["stems"]] == ["Vocals", "Instrumental", "custom_name"]
    assert value["stems"][0]["file"] == {"path": "/c/song_(Vocals)_m.wav", "meta": {"_type": "gradio.FileData"}}
    assert value["sample_rate"] is None  # unreadable: the browser picks the rate
    assert mixer_value(None, paths)["name"] == "stems_mix"
    assert mixer_value("song.wav", ["/c/song_(Vocals)_m.wav"] + [None] * 5) is None  # nothing to mix


def test_mixer_value_reads_the_sample_rate(tmp_path):
    stems = []
    for name in ("a_(Vocals)_m.wav", "a_(Instrumental)_m.wav"):
        sf.write(tmp_path / name, np.zeros((441, 2), dtype="float32"), 44100)
        stems.append(str(tmp_path / name))
    assert mixer_value("a.wav", stems)["sample_rate"] == 44100


def test_mixer_update_hides_the_mixer_without_two_stems():
    shown, value = mixer_update("song.wav", "/c/a_(Vocals)_m.wav", "/c/a_(Drums)_m.wav")
    assert shown["visible"] is True and len(value["stems"]) == 2
    hidden, value = mixer_update("song.wav", None, None)
    assert hidden["visible"] is False and value is None


def test_mixer_is_chained_after_separating_without_changing_the_api(app):
    mixers = [b for b in app.blocks.values() if type(b).__name__ == "HTML" and "uvr-mixer" in b.html_template]
    assert len(mixers) == 6  # five architecture tabs + Ensemble
    for name in ("separate_roformer", "separate_mdxnet", "separate_ensemble"):
        fn = find_fn(app, name)
        assert len(fn.outputs) == 7  # six stems + zip, as before
        mixer_steps = [f for f in app.fns.values() if f.fn is mixer_update and f.trigger_after == fn._id]
        assert len(mixer_steps) == 1 and mixer_steps[0].trigger_only_on_success
        assert mixer_steps[0].outputs[1] in mixers


def test_page_and_gradio_language_follow_the_app_language():
    assert a11y.page_language("pt_BR") == "pt-BR"
    locales = [a11y.gradio_locale(code) for code in ("es_ES", "pt_BR", "zh_CN", "it_IT", "vi_VN")]
    assert locales == ["es", "pt-BR", "zh-CN", "en", "en"]  # Gradio has no Italian or Vietnamese texts
    head = a11y.head_html("es_ES")
    assert head.startswith("<script>") and head.endswith("</script>")
    assert '"page_lang": "es-ES"' in head and "__CONFIG__" not in head


def test_launch_adds_the_accessibility_fixes(ctx):
    kwargs = launch_kwargs(ctx)
    assert kwargs["head"].startswith("<script>")
    assert ":focus-visible" in kwargs["css"]
    # Gradio's progress announcement reads this key, which no Gradio language defines
    assert kwargs["i18n"].translations_dict == {"en": {"common.complete": "Complete"}}
    assert a11y.gradio_i18n("pt_BR").translations_dict.keys() == {"pt-BR"}


def test_announcements():
    stems = a11y.announce_stems("/c/song_(Vocals)_m.wav", None, "/c/song_(Instrumental)_m.flac")
    assert stems["text"] == "Separation finished: Vocals, Instrumental"
    assert a11y.announce("Hi")["id"] != a11y.announce("Hi")["id"]  # repeated messages are read again
    batch = a11y.announce_batch("2 audio files found\nDone: 2 separated, 0 failed. Output: /out")
    assert batch["text"] == "Batch separation finished. Done: 2 separated, 0 failed. Output: /out"
    assert a11y.announce_batch(None)["text"] == "Batch separation finished."


def test_model_filter_announces_the_size_of_the_list(ctx):
    update, message = _model_choices(ctx, SPECS["roformer"], downloaded_only=False)
    assert len(update["choices"]) == 92
    assert message["text"] == "Models in the list: 92"


LABELLED = ("Textbox", "Dropdown", "Slider", "Checkbox", "CheckboxGroup", "Radio", "Number", "Audio", "File")


def test_every_control_has_a_label_and_buttons_are_distinct(app):
    # Screen readers announce controls by their label: none may be empty, and two buttons in
    # the same tab may not share a name (e.g. the single and batch "Separate!" buttons)
    unlabelled = [f"{type(b).__name__} #{b._id}" for b in app.blocks.values()
                  if type(b).__name__ in LABELLED and not str(b.label or "").strip()]
    assert not unlabelled

    def buttons(block):
        for child in getattr(block, "children", []):
            if type(child).__name__ == "Button":
                yield str(child.value)
            elif type(child).__name__ == "DownloadButton":
                yield str(child.label)  # its text; the value is the file
            yield from buttons(child)

    for tab in (b for b in app.blocks.values() if type(b).__name__ == "Tab"):
        names = list(buttons(tab))
        assert len(names) == len(set(names)), (tab.label, names)

