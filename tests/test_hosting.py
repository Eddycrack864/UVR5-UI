"""Hugging Face Space mode: shared-server restrictions and ZeroGPU support."""

import os
import pickle
import sys
import time
import types
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

gr = pytest.importorskip("gradio")

from uvr5_ui import hosting, paths  # noqa: E402
from uvr5_ui.core.models.catalog import ModelCatalog  # noqa: E402
from uvr5_ui.core.separation.ensemble import EnsembleMember, EnsembleOptions  # noqa: E402
from uvr5_ui.core.separation.runtime import RuntimeOptions  # noqa: E402
from uvr5_ui.core.separation.service import StemResult  # noqa: E402
from uvr5_ui.core.separation.specs import ARCHITECTURES_BY_ID as SPECS  # noqa: E402
from uvr5_ui.ui import gpu  # noqa: E402
from uvr5_ui.ui.app import create_app  # noqa: E402
from tests.test_ui import ENSEMBLE_MODELS, NoProgress, ctx, find_fn, kwargs_of, wav_separator  # noqa: E402,F401


@pytest.fixture
def on_space(monkeypatch):
    monkeypatch.setenv("SPACE_ID", "Eddycrack864/UVR5-UI")


def api_names(app) -> set:
    return {f.api_name for f in app.fns.values() if f.api_name}


def test_local_run_is_not_hosted(monkeypatch):
    monkeypatch.delenv("SPACE_ID", raising=False)
    monkeypatch.delenv("SPACES_ZERO_GPU", raising=False)
    assert not hosting.on_space() and not hosting.on_zerogpu()

    def fn():
        pass

    assert hosting.gpu(fn, duration=60) is fn


def test_gpu_wraps_with_spaces_on_zerogpu(monkeypatch):
    calls = []

    def GPU(duration):
        calls.append(duration)
        return lambda fn: ("wrapped", fn)

    monkeypatch.setitem(sys.modules, "spaces", types.SimpleNamespace(GPU=GPU))
    monkeypatch.setenv("SPACES_ZERO_GPU", "true")

    def fn():
        pass

    assert hosting.gpu(fn, duration=gpu._separate_duration) == ("wrapped", fn)
    assert calls == [gpu._separate_duration]


def test_space_hides_what_changes_the_shared_server(ctx, on_space):
    app = create_app(ctx)

    tabs = [b.label for b in app.blocks.values() if type(b).__name__ == "Tab"]
    assert tabs == ["BS/Mel Roformer", "MDX23C", "MDX-NET", "VR ARCH", "Demucs", "Ensemble", "Leaderboard", "Credits"]
    assert not {name for name in api_names(app) if name.startswith("batch_")}
    assert {"separate_roformer", "separate_ensemble", "download_link_roformer"} <= api_names(app)
    batch = [b for b in app.blocks.values() if getattr(b, "label", None) == "Batch separation"]
    assert batch and not any(b.visible for b in batch)
    presets = [b for b in app.blocks.values() if getattr(b, "label", None) == "Manage presets"]
    assert len(presets) == 1 and not presets[0].visible
    assert not [f for f in app.fns.values() if f.name in ("run_save_preset", "run_delete_preset")]


def test_local_app_keeps_batch_and_settings(ctx, monkeypatch):
    monkeypatch.delenv("SPACE_ID", raising=False)
    app = create_app(ctx)
    assert {"batch_roformer", "batch_ensemble"} <= api_names(app)
    assert find_fn(app, "run_save_preset")


def test_space_separations_get_their_own_output_folder(ctx, tmp_root, wav_separator, on_space):
    old = tmp_root / "outputs" / "old_visitor"
    old.mkdir()
    an_hour_ago = time.time() - gpu.OUTPUT_MAX_AGE - 1
    os.utime(old, (an_hour_ago, an_hour_ago))
    app = create_app(ctx)
    fn = find_fn(app, "separate_ensemble")
    audio = tmp_root / "song.wav"
    audio.touch()

    updates = fn.fn(**kwargs_of(fn, models=ENSEMBLE_MODELS, audio=str(audio)), progress=NoProgress())

    stem = Path(updates[0]["value"])
    assert stem.parent.parent == tmp_root / "outputs" and len(stem.parent.name) == 32
    assert not old.exists()


def test_gpu_call_arguments_are_picklable(tmp_root):
    """On ZeroGPU they are sent to the GPU worker process."""
    catalog = ModelCatalog.from_file(tmp_root / "assets" / "models.json")
    model = catalog.by_filename(ENSEMBLE_MODELS[0])
    member = EnsembleMember(SPECS[model.arch], model, {"hop_length": 1024})
    values = [model, member, EnsembleOptions(), RuntimeOptions(), StemResult("a.wav", "Vocals"),
              tmp_root / "outputs", gr.Progress(track_tqdm=True)]
    assert pickle.loads(pickle.dumps(values))[:5] == values[:5]


def test_gpu_seconds_follow_the_audio_length(tmp_path):
    audio = tmp_path / "minute.wav"
    sf.write(audio, np.zeros((44100 * 60, 2), dtype="float32"), 44100)

    assert gpu.gpu_seconds(str(audio)) == gpu.BASE_SECONDS + 60 * gpu.SECONDS_PER_AUDIO_SECOND
    assert gpu.gpu_seconds(str(audio), model_count=2) == 2 * gpu.gpu_seconds(str(audio))
    assert gpu.gpu_seconds(str(audio), model_count=100) == gpu.MAX_SECONDS
    unreadable = gpu.BASE_SECONDS + gpu.UNKNOWN_AUDIO_SECONDS * gpu.SECONDS_PER_AUDIO_SECOND
    assert gpu.gpu_seconds(str(tmp_path / "missing.mp3")) == int(unreadable)


def test_zerogpu_downloads_models_before_asking_for_a_gpu(tmp_root, monkeypatch):
    downloaded = []
    monkeypatch.setattr(gpu, "ensure_downloaded", lambda model, models_dir, report: downloaded.append(model.id))
    model = ModelCatalog.from_file(tmp_root / "assets" / "models.json").by_filename(ENSEMBLE_MODELS[0])

    monkeypatch.delenv("SPACES_ZERO_GPU", raising=False)
    gpu.prefetch([model], NoProgress())
    assert downloaded == []

    monkeypatch.setenv("SPACES_ZERO_GPU", "true")
    gpu.prefetch([model], NoProgress())
    assert downloaded == [model.id]


def test_zerogpu_never_compiles(monkeypatch, ctx):
    ctx.config.set("performance.torch_compile", True)
    monkeypatch.delenv("SPACES_ZERO_GPU", raising=False)
    assert RuntimeOptions.from_config(ctx.config).torch_compile
    monkeypatch.setenv("SPACES_ZERO_GPU", "true")
    assert not RuntimeOptions.from_config(ctx.config).torch_compile


def test_space_uses_the_port_hugging_face_assigns(monkeypatch):
    import uvr5_ui.main as main

    launched = {}

    class FakeApp:
        def queue(self):
            return self

        def launch(self, **kwargs):
            launched.update(kwargs)

    monkeypatch.setattr("uvr5_ui.ui.app.create_app", lambda ctx: FakeApp())
    monkeypatch.setattr("uvr5_ui.ui.app.launch_kwargs", lambda ctx: {})
    monkeypatch.setattr("uvr5_ui.ui.context.AppContext.create", classmethod(lambda cls: None))
    monkeypatch.setattr(main, "migrate_legacy_user_data", lambda: None)
    monkeypatch.setattr(main, "get_config", lambda: types.SimpleNamespace(get=lambda key, default=None: False))
    monkeypatch.setenv("SPACE_ID", "Eddycrack864/UVR5-UI")
    main.main([])
    assert launched["server_port"] is None
    monkeypatch.delenv("SPACE_ID")
    main.main([])
    assert launched["server_port"] == 9999
