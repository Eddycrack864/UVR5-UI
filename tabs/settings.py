import gradio as gr
import os, sys
from assets.i18n.i18n import I18nAuto

import assets.themes.loadThemes as loadThemes

i18n = I18nAuto()

now_dir = os.getcwd()
sys.path.append(now_dir)


def select_themes_tab():
    with gr.Column():
        themes_select = gr.Dropdown(
            choices=loadThemes.get_list(),
            value=loadThemes.read_json(),
            label=i18n("Theme"),
            info=i18n(
                "Select the theme you want to use. (Requires restarting the App)"
            ),
            visible=True,
        )
        themes_select.change(
            fn=loadThemes.select_theme,
            inputs=themes_select,
            outputs=[],
        )
