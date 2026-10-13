import json
import shutil

import numpy as np
import pytest

sf = pytest.importorskip("soundfile")

from uvr5_ui.core.audio import load_audio, normalize_peak, write_audio  # noqa: E402
from uvr5_ui.core.errors import SeparationError  # noqa: E402
from uvr5_ui.core.models.catalog import Model, ModelCatalog  # noqa: E402
from uvr5_ui.core.separation import ensemble, runtime  # noqa: E402
from uvr5_ui.core.separation.ensemble import (  # noqa: E402
    ALGORITHMS, STEM_NAME_MAP, EnsembleConfigError, EnsembleMember, EnsembleOptions, canonical_stem,
    check_ensemble, ensemble_batch, ensemble_file,
)
from uvr5_ui.core.separation.ensemble_presets import PresetStore, bundled_presets_file, parse_presets  # noqa: E402
from uvr5_ui.core.separation.runtime import SeparatorCache  # noqa: E402
from uvr5_ui.core.separation.specs import ARCHITECTURES_BY_ID  # noqa: E402
from tests.conftest import REPO_ROOT  # noqa: E402

SR = 44100
ROFORMER = ARCHITECTURES_BY_ID["roformer"]
MDXNET = ARCHITECTURES_BY_ID["mdxnet"]
DEMUCS = ARCHITECTURES_BY_ID["demucs"]

# model filename -> (stems it writes, peak amplitude of every stem)
MODEL_OUTPUTS = {
    "a.ckpt": (["Vocals", "Instrumental"], 0.2),
    "b.onnx": (["Vocals", "Instrumental"], 0.4),
    "two_stem.onnx": (["Vocals", "Other"], 0.4),
    "htdemucs.yaml": (["Vocals", "Drums", "Bass", "Other"], 0.4),
    "drums.onnx": (["Drums", "No Drums"], 0.4),
}


class WavSeparator:
    """Writes a constant-amplitude stereo WAV per stem, like audio-separator names them."""

    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.loaded = []
        WavSeparator.instances.append(self)

    def load_model(self, model_filename):
        self.loaded.append(model_filename)

    def separate(self, path):
        if "corrupt" in str(path):
            raise RuntimeError("cannot decode")
        model = self.loaded[-1]
        stems, amplitude = MODEL_OUTPUTS[model]
        base = path.replace("\\", "/").rsplit("/", 1)[-1].rsplit(".", 1)[0]
        names = []
        for stem in stems:
            name = f"{base}_({stem})_{model.split('.')[0]}.wav"
            sf.write(f"{self.kwargs['output_dir']}/{name}", np.full((SR // 10, 2), amplitude, np.float32), SR,
                     subtype="PCM_24")
            names.append(name)
        return names


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    monkeypatch.setattr(runtime, "use_autocast", lambda: False)
    WavSeparator.instances.clear()


@pytest.fixture
def cache():
    return SeparatorCache(factory=WavSeparator)


def member(spec, filename, **values):
    return EnsembleMember(spec, Model(filename, spec.id, filename), values)


def run(members, tmp_path, cache, audio_name="song.wav", **options):
    audio = tmp_path / audio_name
    audio.touch()
    return ensemble_file(members, str(audio), "wav", EnsembleOptions(**options), output_dir=tmp_path / "out",
                         cache=cache, work_dir=tmp_path / "work")


def peak(path):
    return float(np.abs(sf.read(path)[0]).max())


def test_algorithms_match_audio_separator():
    pytest.importorskip("audio_separator")
    from audio_separator.separator import Separator

    assert ALGORITHMS == tuple(Separator.VALID_ENSEMBLE_ALGORITHMS)


def test_stem_names_extend_audio_separator():
    pytest.importorskip("audio_separator")
    from audio_separator.separator.separator import STEM_NAME_MAP as UPSTREAM

    assert UPSTREAM.items() <= STEM_NAME_MAP.items()


@pytest.mark.parametrize("raw, stems, expected", [
    ("vocals", ["vocals", "instrumental"], "Vocals"),
    ("Other", ["Vocals", "Other"], "Instrumental"),
    ("Other", ["Vocals", "Drums", "Bass", "Other"], "Other"),
    ("No Vocals", ["Vocals", "No Vocals"], "Instrumental"),
    ("Karaoke", ["Vocals", "Karaoke"], "Instrumental"),
    ("Lead Vocals", ["Lead Vocals", "Backing Vocals"], "Lead Vocals"),
    ("No Reverb", ["Reverb", "No Reverb"], "No Reverb"),
])
def test_canonical_stem(raw, stems, expected):
    assert canonical_stem(raw, stems) == expected


def test_check_ensemble():
    check_ensemble(2, "avg_wave", None)
    check_ensemble(2, "min_fft", [1, 2, 3])  # weights are ignored by non-averaging algorithms
    for args, field in [
        ((1, "avg_wave", None), "models"),
        ((7, "avg_wave", None), "models"),
        ((2, "nope", None), "algorithm"),
        ((2, "avg_fft", [1.0]), "weights"),
        ((2, "avg_wave", [0, 0]), "weights"),
        ((2, "avg_wave", [1, -1]), "weights"),
        ((2, "avg_wave", [1, "x"]), "weights"),
    ]:
        with pytest.raises(EnsembleConfigError) as error:
            check_ensemble(*args)
        assert error.value.field == field


def test_ensemble_averages_matching_stems(tmp_path, cache):
    results = run([member(ROFORMER, "a.ckpt", overlap=4), member(MDXNET, "b.onnx")], tmp_path, cache)

    assert [r.label for r in results] == ["Vocals", "Instrumental"]
    assert results[0].path == str(tmp_path / "out" / "song_(Vocals)_ensemble_avg_wave.wav")
    assert peak(results[0].path) == pytest.approx(0.3, abs=1e-3)
    assert sf.info(results[0].path).subtype == "PCM_24"  # keeps the members' bit depth
    # each member runs with the settings of its own architecture and writes every stem
    roformer, mdxnet = WavSeparator.instances
    assert roformer.kwargs["mdxc_params"]["overlap"] == 4 and roformer.kwargs["output_single_stem"] is None
    assert "mdx_params" in mdxnet.kwargs
    assert not (tmp_path / "work").exists()


def test_weights_and_name(tmp_path, cache):
    results = run([member(ROFORMER, "a.ckpt"), member(MDXNET, "b.onnx")], tmp_path, cache,
                  algorithm="avg_wave", weights=(3, 1), name="my preset")
    assert results[0].path.endswith("song_(Vocals)_ensemble_my_preset.wav")
    assert peak(results[0].path) == pytest.approx(0.25, abs=1e-3)


def test_max_algorithm_and_normalization(tmp_path, cache):
    results = run([member(ROFORMER, "a.ckpt"), member(MDXNET, "b.onnx")], tmp_path, cache,
                  algorithm="max_wave", normalization_threshold=0.9, amplification_threshold=0.8)
    assert peak(results[0].path) == pytest.approx(0.8, abs=1e-3)  # max is 0.4, amplified to 0.8


def test_only_shared_stems_unless_requested(tmp_path, cache):
    members = [member(DEMUCS, "htdemucs.yaml"), member(MDXNET, "two_stem.onnx")]
    assert [r.label for r in run(members, tmp_path, cache)] == ["Vocals"]
    labels = [r.label for r in run(members, tmp_path, cache, include_unmatched=True)]
    assert labels == ["Vocals", "Drums", "Bass", "Other", "Instrumental"]


def test_no_shared_stem_fails(tmp_path, cache):
    with pytest.raises(SeparationError, match="no stem in common"):
        run([member(MDXNET, "drums.onnx"), member(ROFORMER, "a.ckpt")], tmp_path, cache)


def test_keep_intermediates(tmp_path, cache):
    run([member(ROFORMER, "a.ckpt"), member(MDXNET, "b.onnx")], tmp_path, cache, keep_intermediates=True)
    parts = sorted(p.name for p in (tmp_path / "out" / "song_ensemble_parts").iterdir())
    assert parts == ["song_(Instrumental)_a.wav", "song_(Instrumental)_b.wav", "song_(Vocals)_a.wav",
                     "song_(Vocals)_b.wav"]


def test_invalid_setup_fails_before_separating(tmp_path, cache):
    with pytest.raises(EnsembleConfigError):
        run([member(ROFORMER, "a.ckpt")], tmp_path, cache)
    with pytest.raises(SeparationError):
        ensemble_file([member(ROFORMER, "a.ckpt"), member(MDXNET, "b.onnx")], None, "wav", EnsembleOptions(),
                      cache=cache)
    assert WavSeparator.instances == []


def test_batch_loads_each_model_once_per_group(tmp_path, cache, monkeypatch):
    monkeypatch.setattr(ensemble, "GROUP_SIZE", 2)
    src = tmp_path / "in"
    src.mkdir()
    for name in ("a.wav", "b.flac", "corrupt.mp3", "notes.txt"):
        (src / name).touch()

    log = list(ensemble_batch([member(ROFORMER, "a.ckpt"), member(MDXNET, "b.onnx")], str(src),
                              str(tmp_path / "out"), "flac", EnsembleOptions(), cache=cache,
                              work_dir=tmp_path / "work"))

    assert log[0] == "3 audio files found"
    # 2 groups (a+b, corrupt) x 2 models
    assert [s.loaded for s in WavSeparator.instances] == [["a.ckpt"], ["b.onnx"], ["a.ckpt"], ["b.onnx"]]
    assert any(line.startswith("Error separating corrupt.mp3") for line in log)
    assert log[-1].startswith("Done: 2 ensembled, 1 failed")
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == [
        "a_(Instrumental)_ensemble_avg_wave.flac", "a_(Vocals)_ensemble_avg_wave.flac",
        "b_(Instrumental)_ensemble_avg_wave.flac", "b_(Vocals)_ensemble_avg_wave.flac",
    ]


def test_write_audio_formats(tmp_path):
    wave = np.stack([np.linspace(-0.5, 0.5, SR // 10), np.zeros(SR // 10)]).astype(np.float32)
    write_audio(tmp_path / "x.wav", wave, SR, subtype="PCM_24")
    assert sf.info(str(tmp_path / "x.wav")).subtype == "PCM_24"
    write_audio(tmp_path / "x.ogg", wave, SR, subtype="PCM_24")  # unsupported subtype falls back
    assert load_audio(tmp_path / "x.ogg", SR).shape[0] == 2
    if shutil.which("ffmpeg"):
        write_audio(tmp_path / "x.mp3", wave, SR)
        assert load_audio(tmp_path / "x.mp3", SR).shape[0] == 2
    with pytest.raises(ValueError):
        write_audio(tmp_path / "x.xyz", wave, SR)
    assert sorted(p.name for p in tmp_path.iterdir() if ".part" in p.name) == []


def test_normalize_peak():
    wave = np.array([[0.5, -1.0]])
    assert np.abs(normalize_peak(wave, 0.9)).max() == pytest.approx(0.9)
    assert np.abs(normalize_peak(wave * 0.1, 0.9, 0.5)).max() == pytest.approx(0.5)
    assert np.abs(normalize_peak(wave * 0.1, 0.9)).max() == pytest.approx(0.1)


def test_bundled_presets_use_catalog_models():
    if bundled_presets_file() is None:
        pytest.skip("audio-separator is not installed")
    catalog = ModelCatalog.from_file(REPO_ROOT / "assets" / "models.json")
    presets = PresetStore(user_file=REPO_ROOT / "missing.json").bundled()
    assert {"vocal_balanced", "instrumental_clean", "karaoke"} <= {p.id for p in presets}
    for preset in presets:
        assert all(catalog.by_filename(f) for f in preset.models), preset.id


def test_invalid_presets_are_skipped():
    presets = parse_presets({"presets": {
        "ok": {"name": "Ok", "models": ["a", "b"], "algorithm": "min_fft", "weights": None},
        "one_model": {"models": ["a"]},
        "bad_algorithm": {"models": ["a", "b"], "algorithm": "nope"},
        "bad_weights": {"models": ["a", "b"], "algorithm": "avg_wave", "weights": [1]},
        "no_models": {"name": "x"},
    }})
    assert [p.id for p in presets] == ["ok"]


def test_user_presets(tmp_path):
    bundled = tmp_path / "bundled.json"
    bundled.write_text(json.dumps({"version": 1, "presets": {
        "vocal_x": {"name": "Vocal X", "models": ["a", "b"], "algorithm": "avg_fft", "weights": None},
    }}), encoding="utf-8")
    store = PresetStore(user_file=tmp_path / "user" / "presets.json", bundled_file=bundled)

    saved = store.save("My Vocals!", ["a", "b", "c"], "avg_wave", [2, 1, 1], "  mine ")
    assert saved.id == "user_my_vocals" and saved.is_user
    assert [p.id for p in store.all()] == ["vocal_x", "user_my_vocals"]
    assert store.get("user_my_vocals").weights == (2.0, 1.0, 1.0)
    assert store.get("user_my_vocals").description == "mine"

    store.save("my vocals", ["a", "b"], "max_fft")  # same id: overwritten
    assert store.get("user_my_vocals").models == ("a", "b")
    with pytest.raises(EnsembleConfigError):
        store.save("", ["a", "b"], "avg_wave")
    with pytest.raises(EnsembleConfigError):
        store.save("x", ["a"], "avg_wave")

    assert store.delete("vocal_x") is False
    assert store.delete("user_my_vocals") is True
    assert [p.id for p in store.all()] == ["vocal_x"]
