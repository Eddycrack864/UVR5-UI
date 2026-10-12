import gradio as gr

from uvr5_ui.core.leaderboard import COLUMNS, STEM_FILTERS, get_leaderboard
from uvr5_ui.i18n import i18n
from uvr5_ui.ui.adapters import user_errors


def render_leaderboard_tab() -> None:
    with gr.TabItem(i18n("Leaderboard")):
        with gr.Group():
            with gr.Row(equal_height=True):
                list_filter = gr.Dropdown(
                    label=i18n("List filter"),
                    info=i18n("Filter and sort the model list by stem"),
                    choices=STEM_FILTERS,
                    value=lambda: None,
                )
                list_button = gr.Button(i18n("Show list!"), variant="primary")
        table = gr.Dataframe(
            headers=COLUMNS,
            label=i18n("Leaderboard"),
            interactive=False,
            wrap=True,
        )

    list_button.click(user_errors(get_leaderboard), inputs=[list_filter], outputs=[table], api_name="leaderboard")
