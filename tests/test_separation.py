import inspect
import json
import subprocess
import sys

import pytest

from uvr5_ui.core.audio import (
    DEFAULT_NAME_TEMPLATE, check_name_template, list_audio_files, parse_stem_label, render_name, rename_output,
)
from uvr5_ui.core.errors import SeparationError
from uvr5_ui.core.models.catalog import Model
from uvr5_ui.core.separation import runtime
from uvr5_ui.core.separation.runtime import RuntimeOptions, SeparatorCache, execution_summary
from uvr5_ui.core.separation.service import clean_path, is_folder, separate_batch, separate_file
from uvr5_ui.core.separation.specs import (
    ARCHITECTURES, ARCHITECTURES_BY_ID, ENSEMBLE_PARAMS, ENSEMBLE_SECTION, build_separator_kwargs,
)
from tests.conftest import REPO_ROOT

# Keys that live in a settings section but are not separation parameters
UI_ONLY_KEYS = {"model", "output_format", "link", "input_path", "output_path"}


class NoBackendError(Exception):
    """Like audioread's NoBackendError, which audio-separator raises with an empty message."""


class FakeSeparator:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.loaded = []
        self.separated = []
        FakeSeparator.instances.append(self)

    def load_model(self, model_filename):
        self.loaded.append(model_filename)

    def separate(self, path):
        if "corrupt" in str(path):
            raise RuntimeError("cannot decode")
        if "unreadable" in str(path):
            raise NoBackendError()
        if "swallowed" in str(path):
            return []  # older audio-separator versions logged per-file errors and returned nothing
        self.separated.append(path)
        return [f"song_(Vocals)_{self.loaded[-1]}.wav", f"song_(Instrumental)_{self.loaded[-1]}.wav"]


@pytest.fixture(autouse=True)
def no_torch(monkeypatch):
    monkeypatch.setattr(runtime, "use_autocast", lambda: False)
    FakeSeparator.instances.clear()


@pytest.fixture
def cache():
    return SeparatorCache(factory=FakeSeparator)


MODEL = Model("UVR-MDX-NET-Inst_HQ_3.onnx", "mdxnet", "UVR-MDX-NET-Inst_HQ_3.onnx")
MDXNET = ARCHITECTURES_BY_ID["mdxnet"]


def test_spec_keys_match_default_settings():
    defaults = json.loads((REPO_ROOT / "assets" / "default_settings.json").read_text(encoding="utf-8"))
    assert list(defaults) == [s.settings_section for s in ARCHITECTURES] + [ENSEMBLE_SECTION]
    for spec in ARCHITECTURES:
        section = defaults[spec.settings_section]
        assert {p.key for p in spec.params} == set(section) - UI_ONLY_KEYS, spec.id
        for p in spec.params:
            assert section[p.key] == p.default, (spec.id, p.key)

    ensemble = defaults[ENSEMBLE_SECTION]
    assert {p.key for p in ENSEMBLE_PARAMS} == set(ensemble) - UI_ONLY_KEYS - {"preset", "models", "algorithm", "weights"}
    for p in ENSEMBLE_PARAMS:
        assert ensemble[p.key] == p.default, p.key


def test_separator_kwargs_mapping():
    vr = build_separator_kwargs(ARCHITECTURES_BY_ID["vrarch"], {"tta": False, "post_process": True, "single_stem": "  "})
    assert vr["vr_params"]["enable_tta"] is False
    assert vr["vr_params"]["enable_post_process"] is True
    assert vr["output_single_stem"] is None
    assert vr["normalization_threshold"] == 0.9

    mdx = build_separator_kwargs(MDXNET, {"denoise": False, "single_stem": "Instrumental"})
    assert mdx["mdx_params"]["enable_denoise"] is False
    assert mdx["output_single_stem"] == "Instrumental"

    roformer = build_separator_kwargs(ARCHITECTURES_BY_ID["roformer"], {"override_segment_size": True})
    assert roformer["mdxc_params"]["override_model_segment_size"] is True
    assert roformer["mdxc_params"]["overlap"] == 8 and roformer["mdxc_params"]["pitch_shift"] == 0
    assert "model_overlap" not in roformer["mdxc_params"]
    assert not ARCHITECTURES_BY_ID["roformer"].param("batch_size").visible
    assert ARCHITECTURES_BY_ID["mdx23c"].param("batch_size").visible

    mdx23c = build_separator_kwargs(ARCHITECTURES_BY_ID["mdx23c"], {"model_overlap": True, "pitch_shift": -2})
    assert mdx23c["mdxc_params"]["overlap"] is None  # audio-separator then reads the model's YAML
    assert mdx23c["mdxc_params"]["pitch_shift"] == -2

    assert mdx["invert_using_spec"] is False
    assert build_separator_kwargs(MDXNET, {"invert_spec": True})["invert_using_spec"] is True

    demucs = build_separator_kwargs(ARCHITECTURES_BY_ID["demucs"], {})
    assert "output_single_stem" not in demucs
    assert demucs["demucs_params"]["segments_enabled"] is True


def test_separator_kwargs_are_accepted_by_audio_separator():
    pytest.importorskip("audio_separator")
    from audio_separator.separator import Separator

    signature = inspect.signature(Separator.__init__)
    for spec in ARCHITECTURES:
        kwargs = build_separator_kwargs(spec, {})
        assert set(kwargs) <= set(signature.parameters), spec.id
        known = set(signature.parameters[spec.params_group].default)
        # Demucs' batch_size has always been passed through although Separator ignores it
        assert set(kwargs[spec.params_group]) - {"batch_size"} <= known, spec.id


def test_separate_file_returns_labelled_stems(cache, tmp_path):
    stems = separate_file(MDXNET, MODEL, "in.wav", "wav", {}, output_dir=tmp_path, cache=cache)
    assert [s.label for s in stems] == ["Vocals", "Instrumental"]
    assert stems[0].path.startswith(str(tmp_path))
    sep = FakeSeparator.instances[0]
    assert sep.kwargs["output_format"] == "wav"
    assert sep.kwargs["output_dir"] == str(tmp_path)


def test_model_is_reused_between_runs(cache, tmp_path):
    separate_file(MDXNET, MODEL, "a.wav", "wav", {}, output_dir=tmp_path, cache=cache)
    separate_file(MDXNET, MODEL, "b.wav", "wav", {}, output_dir=tmp_path, cache=cache)
    assert len(FakeSeparator.instances) == 1
    separate_file(MDXNET, MODEL, "c.wav", "wav", {"overlap": 0.5}, output_dir=tmp_path, cache=cache)
    assert len(FakeSeparator.instances) == 2


def test_separate_file_wraps_errors(cache, tmp_path):
    with pytest.raises(SeparationError):
        separate_file(MDXNET, MODEL, "corrupt.wav", "wav", {}, output_dir=tmp_path, cache=cache)
    with pytest.raises(SeparationError):
        separate_file(MDXNET, MODEL, "swallowed.wav", "wav", {}, output_dir=tmp_path, cache=cache)
    with pytest.raises(SeparationError):
        separate_file(MDXNET, MODEL, None, "wav", {}, output_dir=tmp_path, cache=cache)


def test_batch_loads_model_once_and_continues_on_error(cache, tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    for name in ("b.wav", "a.MP3", "corrupt.flac", "swallowed.ogg", "unreadable.wav", "notes.txt"):
        (src / name).touch()
    out = tmp_path / "out"

    log = list(separate_batch(MDXNET, MODEL, str(src), str(out), "wav", {}, cache=cache))

    assert len(FakeSeparator.instances) == 1
    assert FakeSeparator.instances[0].loaded == [MODEL.filename]
    assert log[0] == "5 audio files found"
    assert any("Error separating corrupt.flac" in line for line in log)
    assert any("Error separating swallowed.ogg" in line for line in log)
    assert "Error separating unreadable.wav: NoBackendError" in log
    assert log[-1].startswith("Done: 2 separated, 3 failed")
    assert out.is_dir()


def test_batch_validates_input(cache, tmp_path):
    with pytest.raises(SeparationError):
        list(separate_batch(MDXNET, MODEL, str(tmp_path / "missing"), "", "wav", {}, cache=cache))
    assert list(separate_batch(MDXNET, MODEL, str(tmp_path), "", "wav", {}, cache=cache)) == ["No valid audio files."]


def test_batch_accepts_quoted_paths(cache, tmp_path):
    # Windows' "Copy as path" wraps the path in quotes (issue #71)
    (tmp_path / "song.wav").touch()
    out = tmp_path / "stems"
    log = list(separate_batch(MDXNET, MODEL, f'"{tmp_path}"', f' "{out}" ', "wav", {}, cache=cache))
    assert log[-1].startswith("Done: 1 separated, 0 failed")
    assert out.is_dir()


def test_clean_path(tmp_path):
    assert clean_path(r'  "C:\Users\me\Desktop"  ') == r"C:\Users\me\Desktop"
    assert clean_path("'/home/me/music'") == "/home/me/music"
    assert clean_path('"unbalanced') == '"unbalanced'
    assert clean_path(None) == clean_path('""') == ""
    assert is_folder(f'"{tmp_path}"')
    assert not is_folder('""') and not is_folder("") and not is_folder(None)


def test_parse_stem_label():
    assert parse_stem_label("song_(Vocals)_model_bs_roformer_ep_317_sdr_12.9755.wav") == "Vocals"
    assert parse_stem_label("live_(2020)_(Instrumental)_UVR-MDX-NET-Inst_HQ_3.flac") == "Instrumental"
    assert parse_stem_label("no_stem_here.wav") is None


def test_list_audio_files_is_sorted_and_filtered(tmp_path):
    for name in ("B.wav", "a.flac", "c.txt"):
        (tmp_path / name).touch()
    (tmp_path / "dir.wav").mkdir()
    assert [p.name for p in list_audio_files(tmp_path)] == ["a.flac", "B.wav"]


def test_core_does_not_import_gradio():
    code = (
        "import sys, pkgutil, importlib, uvr5_ui.core as core\n"
        "for m in pkgutil.walk_packages(core.__path__, 'uvr5_ui.core.'):\n"
        "    importlib.import_module(m.name)\n"
        "print('gradio' in sys.modules)\n"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"


class FakeConfig(dict):
    def get(self, key, default=None):
        return super().get(key, default)


def test_runtime_options(monkeypatch):
    assert RuntimeOptions.from_config(FakeConfig()) == RuntimeOptions()
    options = RuntimeOptions.from_config(FakeConfig({
        "performance.precision": "native_fp16", "performance.torch_compile": True,
        "performance.chunk_duration": "600", "performance.use_soundfile": True,
    }))
    assert options.separator_kwargs() == {"use_autocast": False, "use_native_fp16": True, "use_torch_compile": True,
                                          "chunk_duration": 600.0, "use_soundfile": True}
    bad = RuntimeOptions.from_config(FakeConfig({"performance.precision": "fp8", "performance.chunk_duration": "x"}))
    assert bad.precision == "auto" and bad.chunk_duration == 0

    monkeypatch.setattr(runtime, "use_autocast", lambda: True)
    assert RuntimeOptions().separator_kwargs()["use_autocast"] is True
    assert RuntimeOptions().separator_kwargs()["chunk_duration"] is None
    assert RuntimeOptions(precision="fp32").separator_kwargs()["use_autocast"] is False


def test_runtime_kwargs_are_accepted_by_audio_separator():
    pytest.importorskip("audio_separator")
    from audio_separator.separator import Separator

    assert set(RuntimeOptions().separator_kwargs()) <= set(inspect.signature(Separator.__init__).parameters)


def test_runtime_options_reach_the_separator(cache, tmp_path):
    separate_file(MDXNET, MODEL, "a.wav", "wav", {}, output_dir=tmp_path, cache=cache,
                  options=RuntimeOptions(precision="native_fp16", chunk_duration=300))
    kwargs = FakeSeparator.instances[0].kwargs
    assert kwargs["use_native_fp16"] is True and kwargs["chunk_duration"] == 300


def test_execution_summary():
    class Loaded:
        effective_precision = "native_fp16"
        effective_torch_compile = True

    assert execution_summary(Loaded()) == "native_fp16 + torch.compile"
    assert execution_summary(FakeSeparator()) is None


def test_name_templates(tmp_path):
    check_name_template(DEFAULT_NAME_TEMPLATE)
    check_name_template("{stem}/{input}")
    for bad in ("{input}_{model}", "{input}_{stem}_{date}", "{stem", "{0}_{stem}"):
        with pytest.raises(ValueError):
            check_name_template(bad)
    assert render_name("{stem}/{input}: {model}", "song", "Vocals", "m") == "Vocals_song_ m"

    out = tmp_path / "live_(2020)_(Instrumental)_UVR-MDX-NET-Inst_HQ_3.flac"
    out.touch()
    assert rename_output(out, DEFAULT_NAME_TEMPLATE) == out
    renamed = rename_output(out, "{stem} - {input} ({model})")
    assert renamed.name == "Instrumental - live_(2020) (UVR-MDX-NET-Inst_HQ_3).flac"
    assert renamed.exists() and not out.exists()
    assert rename_output(tmp_path / "missing_(Vocals)_m.wav", "{stem}").name == "missing_(Vocals)_m.wav"


def test_runtime_options_name_template():
    assert RuntimeOptions.from_config(FakeConfig({"output.name_template": "{stem}"})).name_template == "{stem}"
    invalid = RuntimeOptions.from_config(FakeConfig({"output.name_template": "{input}"}))
    assert invalid.name_template == DEFAULT_NAME_TEMPLATE
    assert "name_template" not in RuntimeOptions().separator_kwargs()
