"""Shared dependencies handed to every tab renderer."""

from dataclasses import dataclass, field

from uvr5_ui.config.settings import SeparationSettings
from uvr5_ui.config.store import ConfigStore, get_config
from uvr5_ui.core.models.catalog import ModelCatalog, get_catalog
from uvr5_ui.core.separation.ensemble_presets import PresetStore


@dataclass
class AppContext:
    config: ConfigStore
    settings: SeparationSettings
    catalog: ModelCatalog
    initial_settings: dict = field(default_factory=dict)
    presets: PresetStore = field(default_factory=PresetStore)

    @classmethod
    def create(cls) -> "AppContext":
        config = get_config()
        settings = SeparationSettings(config)
        return cls(config=config, settings=settings, catalog=get_catalog(), initial_settings=settings.initial())
