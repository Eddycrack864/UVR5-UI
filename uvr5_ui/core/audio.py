"""Audio file helpers shared by the separation and download services."""

import os
import re
from pathlib import Path

import numpy as np

OUTPUT_FORMATS = ["wav", "flac", "mp3", "ogg", "opus", "m4a", "aiff", "ac3"]
AUDIO_EXTENSIONS = tuple(f".{ext}" for ext in OUTPUT_FORMATS)

# Written with soundfile (lossless/libsndfile) or pydub + ffmpeg (lossy), like audio-separator does
SOUNDFILE_FORMATS = {"wav": "WAV", "flac": "FLAC", "ogg": "OGG", "aiff": "AIFF"}
PYDUB_FORMATS = {"mp3": "mp3", "m4a": "mp4", "opus": "opus", "ac3": "ac3"}

# audio-separator names outputs "<input>_(<Stem>)_<model>.<ext>"
_STEM_RE = re.compile(r"_\(([^()]+)\)")


def list_audio_files(directory: Path) -> list[Path]:
    """Audio files directly inside ``directory`` (not recursive), sorted by name."""
    directory = Path(directory)
    return sorted(
        (p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS),
        key=lambda p: p.name.lower(),
    )


def parse_stem_label(filename: str) -> str | None:
    """Extract the stem name (e.g. ``Vocals``) from an audio-separator output filename."""
    matches = _STEM_RE.findall(Path(filename).stem)
    return matches[-1] if matches else None


def load_audio(path: Path, sample_rate: int) -> np.ndarray:
    """Decode ``path`` as float32 ``(channels, samples)``, resampled to ``sample_rate``."""
    import librosa  # slow to import

    wave, _ = librosa.load(str(path), sr=sample_rate, mono=False)
    return wave[np.newaxis, :] if wave.ndim == 1 else wave


def normalize_peak(wave: np.ndarray, max_peak: float, min_peak: float = 0.0) -> np.ndarray:
    """Scale ``wave`` down to ``max_peak``, or up to ``min_peak`` when it is quieter.

    Same rule as audio-separator's normalization/amplification thresholds.
    """
    if wave.size == 0:
        raise ValueError("Audio data is empty")
    peak = float(np.abs(wave).max())
    if not np.isfinite(peak):
        raise ValueError("Audio data must contain only finite values")
    if peak > max_peak:
        return wave * (max_peak / peak)
    if min_peak and 0 < peak < min_peak:
        return wave * (min_peak / peak)
    return wave


def audio_subtype(path: Path) -> str | None:
    """libsndfile subtype of ``path`` (e.g. ``PCM_24``), or None if it can't be read."""
    import soundfile as sf

    try:
        return sf.info(str(path)).subtype
    except Exception:
        return None


def write_audio(path: Path, wave: np.ndarray, sample_rate: int, subtype: str | None = None) -> Path:
    """Write ``wave`` ``(channels, samples)`` in the format given by ``path``'s extension.

    ``subtype`` (e.g. the input's ``PCM_24``) is used when the format supports it.
    The file is written next to its destination and renamed, so a failure never
    leaves a truncated output behind.
    """
    path = Path(path)
    fmt = path.suffix.lower().lstrip(".")
    data = np.ascontiguousarray(np.asarray(wave, dtype=np.float32).T)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.part{path.suffix}")
    try:
        if fmt in SOUNDFILE_FORMATS:
            import soundfile as sf

            container = SOUNDFILE_FORMATS[fmt]
            if subtype is not None and not sf.check_format(container, subtype):
                subtype = None
            sf.write(str(tmp), data, sample_rate, format=container, subtype=subtype)
        elif fmt in PYDUB_FORMATS:
            from pydub import AudioSegment

            pcm = (np.clip(data, -1.0, 1.0) * 32767).astype(np.int16)
            segment = AudioSegment(pcm.tobytes(), frame_rate=sample_rate, sample_width=2, channels=pcm.shape[1])
            segment.export(str(tmp), format=PYDUB_FORMATS[fmt], bitrate="320k" if fmt == "mp3" else None)
        else:
            raise ValueError(f"Unsupported output format: {fmt}")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
    return path
