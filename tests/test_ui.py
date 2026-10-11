"""UI smoke tests: build the Blocks app without launching it and drive handlers directly."""

import json

import pytest

gr = pytest.importorskip("gradio")

from uvr5_ui.config.settings import SeparationSettings  # noqa: E402
from uvr5_ui.config.store import ConfigStore  # noqa: E402
from uvr5_ui.core.models.catalog import ModelCatalog  # noqa: E402
from uvr5_ui.core.separation import runtime  # noqa: E402
from uvr5_ui.core.separation.runtime import separator_cache  # noqa: E402
from uvr5_ui.ui.app import create_app  # noqa: E402
from uvr5_ui.ui.context import AppContext  # noqa: E402
from tests.test_separation import FakeSeparator  # noqa: E402


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
                      settings.initial())


@pytest.fixture
def app(ctx):
    return create_app(ctx)


def find_fn(app, name, nth=0):
    fns = [f for f in app.fns.values() if getattr(f, "name", None) == name or getattr(f, "api_name", None) == name]
    return fns[nth]


def test_tabs(app):
    labels = [b.label for b in app.blocks.values() if type(b).__name__ == "Tab"]
    assert labels == ["BS/Mel Roformer", "MDX23C", "MDX-NET", "VR ARCH", "Demucs",
                      "Leaderboard", "Themes", "Settings", "Credits"]


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
    assert set(custom) == {"Roformer", "MDX23C", "MDX-NET", "VR Arch", "Demucs"}
    assert custom["Roformer"]["segment_size"] == 512
    assert ctx.config.get("load_custom_settings") is True
    assert ctx.settings.initial()["Roformer"]["segment_size"] == 512

    reset = find_fn(app, "reset_settings")
    updates = reset.fn()
    assert len(updates) == len(save.inputs)
    assert updates[first_segment_index]["value"] == 256
    assert ctx.config.get("load_custom_settings") is False
