import json

from uvr5_ui.config.store import ConfigStore, deep_merge, migrate_legacy_user_data
from uvr5_ui.i18n import AUTO_LANGUAGE, I18nAuto, N_
from uvr5_ui.ui import theme


def make_store(tmp_root):
    return ConfigStore(
        defaults_file=tmp_root / "assets" / "config.default.json",
        user_file=tmp_root / "user_data" / "config.json",
    )


def test_deep_merge_does_not_mutate_inputs():
    base = {"a": {"b": 1, "c": 2}, "d": 3}
    merged = deep_merge(base, {"a": {"b": 10}})
    assert merged == {"a": {"b": 10, "c": 2}, "d": 3}
    assert base["a"]["b"] == 1


def test_defaults_are_read_and_never_written(tmp_root):
    defaults_file = tmp_root / "assets" / "config.default.json"
    before = defaults_file.read_text(encoding="utf-8")
    store = make_store(tmp_root)

    assert store.get("theme.mode") == "dark"
    assert store.get("missing.key", "fallback") == "fallback"

    store.set("theme.mode", "light")
    assert store.get("theme.mode") == "light"
    assert store.get("theme.class") == "NoCrypt/miku"  # untouched default still merged
    assert defaults_file.read_text(encoding="utf-8") == before

    user = json.loads((tmp_root / "user_data" / "config.json").read_text(encoding="utf-8"))
    assert user == {"theme": {"mode": "light"}}


def test_user_overrides_survive_reload(tmp_root):
    make_store(tmp_root).set("lang.selected_lang", "es_ES")
    assert make_store(tmp_root).get("lang.selected_lang") == "es_ES"


def test_corrupt_user_file_falls_back_to_defaults(tmp_root):
    user_file = tmp_root / "user_data" / "config.json"
    user_file.parent.mkdir()
    user_file.write_text("{not json", encoding="utf-8")
    assert make_store(tmp_root).get("theme.mode") == "dark"


def test_migrate_legacy_user_data(tmp_root):
    legacy_config = tmp_root / "assets" / "config.json"
    legacy_config.write_text(json.dumps({"lang": {"override": True, "selected_lang": "es_ES"}}), encoding="utf-8")
    legacy_custom = tmp_root / "assets" / "custom_settings.json"
    legacy_custom.write_text("{}", encoding="utf-8")
    user_config = tmp_root / "user_data" / "config.json"
    custom = tmp_root / "user_data" / "custom_settings.json"

    migrated = migrate_legacy_user_data(legacy_config, user_config, legacy_custom, custom)

    assert len(migrated) == 2
    assert user_config.exists() and custom.exists()
    assert not legacy_custom.exists()
    assert make_store(tmp_root).get("lang.selected_lang") == "es_ES"
    # Second run is a no-op
    assert migrate_legacy_user_data(legacy_config, user_config, legacy_custom, custom) == []


def test_i18n_override_and_fallback(tmp_root):
    store = make_store(tmp_root)
    lang_dir = tmp_root / "assets" / "i18n" / "languages"

    store.set("lang.override", True)
    store.set("lang.selected_lang", "es_ES")
    es = I18nAuto(config=store, lang_dir=lang_dir)
    assert es.language == "es_ES"
    assert es("Select the model") != "Select the model"
    assert es("a key that does not exist") == "a key that does not exist"

    store.set("lang.selected_lang", "xx_XX")  # missing file -> no crash
    assert I18nAuto(config=store, lang_dir=lang_dir).language in es.available_languages()

    assert "en_US" in es.available_languages()
    assert AUTO_LANGUAGE not in es.available_languages()
    assert N_("Segment size") == "Segment size"


def test_theme_selection(tmp_root):
    store = make_store(tmp_root)
    themes_dir = tmp_root / "assets" / "themes"
    (themes_dir / "MyTheme.py").write_text(
        "import gradio as gr\n\nclass Custom(gr.themes.Base):\n    pass\n", encoding="utf-8"
    )

    themes = theme.list_themes(themes_dir)
    assert themes[0] == "MyTheme"
    assert "gradio/soft" in themes

    assert theme.select_theme("gradio/soft", store, themes_dir)
    assert theme.current_theme_name(store) == "gradio/soft"
    assert theme.load_theme(store, themes_dir) == "gradio/soft"

    assert theme.select_theme("MyTheme", store, themes_dir)
    assert store.get("theme.class") == "Custom"
    assert theme.current_theme_name(store) == "MyTheme"

    theme.select_mode("light", store)
    assert theme.current_mode(store) == "light"
