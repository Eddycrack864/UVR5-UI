import sys
import types

import pytest

from uvr5_ui.core.downloads import model_downloader, ytdl
from uvr5_ui.core.downloads.model_downloader import METHOD_PYTHON, download_model, filename_from_url
from uvr5_ui.core.errors import DownloadError
from uvr5_ui.core.models.catalog import Model


def test_filename_from_url():
    assert filename_from_url("https://huggingface.co/x/resolve/main/roformers/model.ckpt?download=true") == "model.ckpt"


def test_python_download_and_skip_existing(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "weights.ckpt").write_bytes(b"x" * 3000)
    (src / "config.yaml").write_text("a: 1")
    model = Model("m", "roformer", "weights.ckpt", {
        "huggingface": [(src / "weights.ckpt").as_uri(), (src / "config.yaml").as_uri()],
    })
    dest = tmp_path / "models"
    seen = []

    log = list(download_model(model, "Hugging Face", METHOD_PYTHON, models_dir=dest,
                              progress=lambda f, d: seen.append(f)))

    assert (dest / "weights.ckpt").read_bytes() == b"x" * 3000
    assert (dest / "config.yaml").exists()
    assert log[-1] == "config.yaml downloaded successfully!"
    assert seen[-1] == 1.0
    assert not list(dest.glob("*.part"))

    again = list(download_model(model, "Hugging Face", METHOD_PYTHON, models_dir=dest))
    assert again == ["weights.ckpt already exists.", "config.yaml already exists."]


def test_source_mapping_uses_huggingface_urls(tmp_path, monkeypatch):
    used = []
    monkeypatch.setattr(model_downloader, "_download_python", lambda url, dest, cb: used.append(url))
    model = Model("m", "mdxnet", "m.onnx", {"github": ["https://github.com/m.onnx"],
                                            "huggingface": ["https://huggingface.co/m.onnx"]})
    list(download_model(model, "Hugging Face", METHOD_PYTHON, models_dir=tmp_path))
    assert used == ["https://huggingface.co/m.onnx"]


def test_missing_external_tool_is_reported(tmp_path, monkeypatch):
    def popen(*args, **kwargs):
        raise FileNotFoundError("wget")
    monkeypatch.setattr(model_downloader.subprocess, "Popen", popen)
    model = Model("m", "mdxnet", "m.onnx", {"github": ["https://github.com/m.onnx"]})
    log = list(download_model(model, "Github", "wget", models_dir=tmp_path))
    assert log[-1] == "Error downloading m.onnx: 'wget' is not installed"


def test_unsupported_method_and_no_urls(tmp_path):
    model = Model("m", "demucs", "m.yaml")
    assert list(download_model(model, "Github", "ftp", models_dir=tmp_path)) == ["Unsupported download method: ftp"]
    assert "No URLs found" in list(download_model(model, "Github", METHOD_PYTHON, models_dir=tmp_path))[0]


class FakeYoutubeDL:
    def __init__(self, opts):
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download):
        assert download is True
        out_dir = self.opts["outtmpl"].rsplit("%(title)s", 1)[0]
        final = f"{out_dir}My Song_ Live.wav"
        open(final, "wb").close()
        return {"title": "My Song: Live", "requested_downloads": [{"filepath": final}]}

    def prepare_filename(self, info):
        raise AssertionError("should use requested_downloads")


def test_ytdl_uses_final_filepath(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "yt_dlp", types.SimpleNamespace(YoutubeDL=FakeYoutubeDL))
    path = ytdl.download_audio(" https://example.com/watch?v=1 ", tmp_path)
    assert path.name == "My Song_ Live.wav"
    assert path.exists()


def test_ytdl_errors(tmp_path, monkeypatch):
    with pytest.raises(DownloadError):
        ytdl.download_audio("  ", tmp_path)

    class Broken(FakeYoutubeDL):
        def extract_info(self, url, download):
            raise RuntimeError("Unsupported URL")

    monkeypatch.setitem(sys.modules, "yt_dlp", types.SimpleNamespace(YoutubeDL=Broken))
    with pytest.raises(DownloadError, match="Unsupported URL"):
        ytdl.download_audio("https://example.com", tmp_path)
