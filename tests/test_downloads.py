import io
import sys
import types
import urllib.error

import pytest

from uvr5_ui.core.downloads import model_downloader, ytdl
from uvr5_ui.core.downloads.model_downloader import (
    METHOD_PYTHON, download_model, ensure_downloaded, file_urls, filename_from_url,
)
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


class FakeResponse:
    def __init__(self, data, status=200, fail_after=None):
        self.status = status
        self.headers = {"Content-Length": str(len(data))}
        self._body = io.BytesIO(data)
        self._fail_after = fail_after

    def read(self, size):
        if self._fail_after is not None and self._body.tell() >= self._fail_after:
            raise ConnectionResetError("connection reset")
        return self._body.read(size if self._fail_after is None else self._fail_after - self._body.tell())

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def no_retry_delay(monkeypatch):
    monkeypatch.setattr(model_downloader, "_RETRY_DELAY", 0)


def test_interrupted_download_resumes_from_the_partial_file(tmp_path, monkeypatch, no_retry_delay):
    data = b"0123456789"
    ranges = []

    def urlopen(request, timeout):
        ranges.append(request.get_header("Range"))
        if len(ranges) == 1:
            return FakeResponse(data, fail_after=4)  # the connection drops after 4 bytes
        start = int(request.get_header("Range")[6:-1])
        return FakeResponse(data[start:], status=206)

    monkeypatch.setattr(model_downloader.urllib.request, "urlopen", urlopen)
    model = Model("m", "roformer", "m.ckpt", {"github": ["https://github.com/m.ckpt"]})

    log = list(download_model(model, "Github", METHOD_PYTHON, models_dir=tmp_path))

    assert ranges == [None, "bytes=4-"]
    assert (tmp_path / "m.ckpt").read_bytes() == data
    assert not (tmp_path / "m.ckpt.part").exists()
    assert log[-1] == "m.ckpt downloaded successfully!"


def test_a_server_that_ignores_the_range_restarts_the_file(tmp_path, monkeypatch, no_retry_delay):
    (tmp_path / "m.ckpt.part").write_bytes(b"stale")
    monkeypatch.setattr(model_downloader.urllib.request, "urlopen",
                        lambda request, timeout: FakeResponse(b"fresh data"))
    model = Model("m", "roformer", "m.ckpt", {"github": ["https://github.com/m.ckpt"]})
    list(download_model(model, "Github", METHOD_PYTHON, models_dir=tmp_path))
    assert (tmp_path / "m.ckpt").read_bytes() == b"fresh data"


def test_client_errors_are_not_retried(tmp_path, monkeypatch, no_retry_delay):
    calls = []

    def urlopen(request, timeout):
        calls.append(request.full_url)
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(model_downloader.urllib.request, "urlopen", urlopen)
    model = Model("m", "roformer", "m.ckpt", {"github": ["https://github.com/m.ckpt"]})
    log = list(download_model(model, "Github", METHOD_PYTHON, models_dir=tmp_path))
    assert calls == ["https://github.com/m.ckpt"]
    assert log[-1] == "Error downloading m.ckpt from github.com: HTTP Error 404: Not Found"


FALLBACK_MODEL = Model("m", "roformer", "m.ckpt", {
    "github": ["https://github.com/m.ckpt", "https://github.com/m.yaml"],
    "huggingface": ["https://huggingface.co/m.ckpt", "https://huggingface.co/m.yaml"],
})


def test_file_urls_put_the_selected_source_first():
    assert file_urls(FALLBACK_MODEL, "Hugging Face") == {
        "m.ckpt": ["https://huggingface.co/m.ckpt", "https://github.com/m.ckpt"],
        "m.yaml": ["https://huggingface.co/m.yaml", "https://github.com/m.yaml"],
    }


def test_a_failed_file_is_downloaded_from_the_other_source(tmp_path, monkeypatch):
    used = []

    def download(url, dest, on_fraction):
        used.append(url)
        if url == "https://github.com/m.ckpt":
            raise ConnectionError("connection closed after 800 MB")
        dest.write_text(url)

    monkeypatch.setattr(model_downloader, "_download_python", download)
    (tmp_path / "m.ckpt.part").write_text("partial from github")

    log = list(download_model(FALLBACK_MODEL, "Github", METHOD_PYTHON, models_dir=tmp_path))

    assert used == ["https://github.com/m.ckpt", "https://huggingface.co/m.ckpt", "https://github.com/m.yaml"]
    assert "Trying another source for m.ckpt..." in log
    assert (tmp_path / "m.ckpt").read_text() == "https://huggingface.co/m.ckpt"
    assert not (tmp_path / "m.ckpt.part").exists()  # not resumed from another source's partial file


def test_ensure_downloaded(tmp_path, monkeypatch):
    used = []
    monkeypatch.setattr(model_downloader, "_download_python",
                        lambda url, dest, cb: (used.append(url), dest.touch()))
    (tmp_path / "m.yaml").touch()
    ensure_downloaded(FALLBACK_MODEL, tmp_path)
    assert used == ["https://github.com/m.ckpt"]  # only the missing file

    ensure_downloaded(FALLBACK_MODEL, tmp_path)
    assert len(used) == 1  # nothing missing: no download at all
    ensure_downloaded(Model("x", "demucs", "x.yaml"), tmp_path)  # no sources: audio-separator handles it


def test_ensure_downloaded_raises_when_every_source_fails(tmp_path, monkeypatch):
    def download(url, dest, on_fraction):
        raise ConnectionError("no connection")

    monkeypatch.setattr(model_downloader, "_download_python", download)
    with pytest.raises(DownloadError, match="could not download m.ckpt, m.yaml"):
        ensure_downloaded(FALLBACK_MODEL, tmp_path)


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
