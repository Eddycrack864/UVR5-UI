"""Audio file helpers shared by the separation and download services."""

import re
from pathlib import Path

OUTPUT_FORMATS = ["wav", "flac", "mp3", "ogg", "opus", "m4a", "aiff", "ac3"]
AUDIO_EXTENSIONS = tuple(f".{ext}" for ext in OUTPUT_FORMATS)

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
