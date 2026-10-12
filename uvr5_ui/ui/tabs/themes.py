import gradio as gr

from uvr5_ui.i18n import i18n
from uvr5_ui.ui import theme
from uvr5_ui.ui.context import AppContext


def render_themes_tab(ctx: AppContext) -> None:
    with gr.TabItem(i18n("Themes")):
        themes_select = gr.Dropdown(
            label=i18n("Theme"),
            info=i18n("Select the theme you want to use. (Requires restarting the App)"),
            choices=theme.list_themes(),
            value=theme.current_theme_name(ctx.config),
            interactive=True,
        )
        mode_select = gr.Dropdown(
            label=i18n("Mode"),
            info=i18n("Select the mode you want to use. (Requires restarting the App)"),
            choices=theme.MODES,
            value=theme.current_mode(ctx.config),
            interactive=True,
        )

    def select_theme(name):
        if theme.select_theme(name, ctx.config):
            gr.Info(f"Theme {name} successfully selected, restart the App.")
        else:
            gr.Warning(f"Theme {name} was not found.")

    def select_mode(mode):
        theme.select_mode(mode, ctx.config)
        gr.Info(f"Mode {mode} successfully selected, restart the App.")

    themes_select.change(select_theme, inputs=[themes_select], api_visibility="undocumented")
    mode_select.change(select_mode, inputs=[mode_select], api_visibility="undocumented")
