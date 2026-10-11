"""Download audio from any site supported by yt-dlp, converted to 32-bit float WAV."""

import logging
from pathlib import Path

from uvr5_ui import paths
from uvr5_ui.core.errors import DownloadError

logger = logging.getLogger(__name__)


def _ydl_options(output_dir: Path) -> dict:
    return {
        "format": "bestaudio/best",
        "noplaylist": True,
        "windowsfilenames": True,  # strip characters that are invalid on Windows (/ : ? " ...)
        "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
            "preferredquality": "32",
        }],
        "postprocessor_args": ["-acodec", "pcm_f32le"],
    }


def _resolve_output(ydl, info: dict) -> Path:
    for download in info.get("requested_downloads") or []:
        if download.get("filepath"):
            return Path(download["filepath"])
    return Path(ydl.prepare_filename(info)).with_suffix(".wav")


def download_audio(url: str, output_dir: Path = None) -> Path:
    if not url or not url.strip():
        raise DownloadError("No link provided")
    import yt_dlp

    output_dir = Path(output_dir or paths.YTDL_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with yt_dlp.YoutubeDL(_ydl_options(output_dir)) as ydl:
            info = ydl.extract_info(url.strip(), download=True)
            path = _resolve_output(ydl, info)
    except Exception as e:
        raise DownloadError(f"Error extracting audio with yt-dlp: {e}") from e

    if not path.exists():
        raise DownloadError(f"yt-dlp finished but the audio file was not found: {path}")
    return path.resolve()
