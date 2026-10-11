"""Model leaderboard from audio-separator's model list (SDR scores per stem)."""

import logging

from uvr5_ui.core.errors import UVRError

logger = logging.getLogger(__name__)

STEM_FILTERS = [
    "vocals", "instrumental", "reverb", "echo", "noise", "crowd", "dry", "aspiration",
    "male", "woodwinds", "kick", "drums", "bass", "guitar", "piano", "other",
]
COLUMNS = ["Model", "Type", "Filename", "Stems"]


def get_leaderboard(stem: str | None) -> list[list[str]]:
    """Rows of ``COLUMNS``, sorted by SDR for ``stem`` (best first) when a stem is given."""
    from audio_separator.separator import Separator

    try:
        separator = Separator(info_only=True, log_level=logging.WARNING)
        models = separator.get_simplified_model_list(filter_sort_by=stem or None)
    except Exception as e:
        raise UVRError(f"Could not load the model list: {e}") from e

    return [
        [info["Name"], info["Type"], filename, ", ".join(info["Stems"])]
        for filename, info in models.items()
    ]
