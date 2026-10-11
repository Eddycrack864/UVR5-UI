import gradio as gr

from uvr5_ui.i18n import i18n

CREDITS = """
UVR5 UI created by **[Eddycrack 864](https://github.com/Eddycrack864).** Join **[AI HUB](https://discord.gg/aihub)** community.
* python-audio-separator by [beveradb](https://github.com/beveradb).
* Special thanks to [Ilaria](https://github.com/TheStingerX) for hosting this space and help.
* Thanks to [Mikus](https://github.com/cappuch) for the help with the code.
* Thanks to [Nick088](https://huggingface.co/Nick088) for the help to fix roformers.
* Thanks to [yt_dlp](https://github.com/yt-dlp/yt-dlp) devs.
* Separation by link source code and improvements by [NeoDev](https://github.com/TheNeodev).
* Thanks to [ArisDev](https://github.com/aris-py) for porting UVR5 UI to Kaggle and improvements.
* Thanks to [Bebra777228](https://github.com/Bebra777228)'s code for guiding me to improve my code.
* Thanks to Nick088, MrM0dZ, Ryouko-Yamanda65777, lucinamari, perariroswe, Enes, Léo, the_undead0 and Storm for helping translate UVR5 UI.
* Thanks to vadigr123 for creating the images for the Discord Rich Presence.

You can donate to the original UVR5 project here:
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/uvr5)
"""


def render_credits_tab() -> None:
    with gr.TabItem(i18n("Credits")):
        gr.Markdown(CREDITS)
