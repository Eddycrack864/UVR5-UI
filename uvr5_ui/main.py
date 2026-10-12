"""Application entry point: parse options, prepare user data and launch Gradio."""

import logging

from uvr5_ui import paths
from uvr5_ui.cli import parse_args
from uvr5_ui.config.store import get_config, migrate_legacy_user_data


def main(argv: list[str] | None = None) -> None:
    options = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    for noisy in ("httpx", "httpcore", "urllib3", "gradio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    migrate_legacy_user_data()

    from uvr5_ui.integrations.discord_presence import presence
    from uvr5_ui.ui.app import create_app, launch_kwargs
    from uvr5_ui.ui.context import AppContext

    if get_config().get("discord_presence", False):
        presence.start()

    try:
        ctx = AppContext.create()
        create_app(ctx).queue().launch(
            share=options.share,
            favicon_path=str(paths.FAVICON),
            server_name=options.server_name,
            server_port=options.listen_port,
            inbrowser=options.open_browser,
            **launch_kwargs(ctx),
        )
    finally:
        presence.stop()
