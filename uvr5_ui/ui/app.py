"""Assembles the Gradio Blocks app from the individual tabs."""

import gradio as gr

from uvr5_ui.core.separation.specs import ARCHITECTURES
from uvr5_ui.i18n import i18n
from uvr5_ui.ui import a11y, theme
from uvr5_ui.ui.context import AppContext
from uvr5_ui.ui.tabs.credits import render_credits_tab
from uvr5_ui.ui.tabs.ensemble import render_ensemble_tab
from uvr5_ui.ui.tabs.leaderboard import render_leaderboard_tab
from uvr5_ui.ui.tabs.separation import render_separation_tab
from uvr5_ui.ui.tabs.settings import render_settings_tab
from uvr5_ui.ui.tabs.themes import render_themes_tab

TITLE = "🎵 UVR5 UI 🎵"
# Every uploaded audio and every returned stem is copied to Gradio's temp cache: once a
# day, delete the files older than a day so it doesn't grow without limit.
DELETE_CACHE = (86400, 86400)


def launch_kwargs(ctx: AppContext) -> dict:
    """App-level options that Gradio 6 takes in ``launch()`` instead of ``gr.Blocks()``."""
    return {
        "theme": theme.load_theme(ctx.config) or theme.DEFAULT_THEME,
        "js": theme.mode_js(theme.current_mode(ctx.config)),
        "head": a11y.head_html(i18n.language),
        "css": a11y.CSS,
    }


def create_app(ctx: AppContext = None) -> gr.Blocks:
    ctx = ctx or AppContext.create()

    # No Gradio telemetry: it reports every launch to huggingface.co
    with gr.Blocks(title=TITLE, analytics_enabled=False, delete_cache=DELETE_CACHE) as app:
        # The emojis are hidden from screen readers, which read them as "musical note".
        # gr.HTML, because the Markdown sanitizer drops aria-hidden
        gr.HTML('<h1><span aria-hidden="true">🎵</span> UVR5 UI <span aria-hidden="true">🎵</span></h1>')
        gr.Markdown(i18n("If you like UVR5 UI you can star my repo on [GitHub](https://github.com/Eddycrack864/UVR5-UI)"))
        gr.Markdown(i18n("Try UVR5 UI on Hugging Face with A100 [here](https://huggingface.co/spaces/TheStinger/UVR5_UI)"))

        with gr.Tabs():
            separation_tabs = [render_separation_tab(spec, ctx) for spec in ARCHITECTURES]
            separation_tabs.append(render_ensemble_tab(ctx, separation_tabs))
            render_leaderboard_tab()
            render_themes_tab(ctx)
            render_settings_tab(ctx, separation_tabs)
            render_credits_tab()

    return app
