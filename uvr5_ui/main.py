"""Application entry point: parse options, prepare user data and launch Gradio."""

import logging

from uvr5_ui import hosting, paths
from uvr5_ui.cli import parse_args
from uvr5_ui.config.store import get_config, migrate_legacy_user_data


def main(argv: list[str] | None = None) -> None:
    options = parse_args(argv)
    if hosting.on_zerogpu():
        import spaces  # noqa: F401  # patches torch, so it goes before anything imports torch
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    for noisy in ("httpx", "httpx2", "httpcore", "urllib3", "gradio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    migrate_legacy_user_data()

    from uvr5_ui.integrations.discord_presence import presence
    from uvr5_ui.ui.app import create_app, launch_kwargs
    from uvr5_ui.ui.context import AppContext

    if get_config().get("discord_presence", False) and not hosting.on_space():
        presence.start()

    try:
        ctx = AppContext.create()
        create_app(ctx).queue().launch(
            share=options.share,
            favicon_path=str(paths.FAVICON),
            server_name=options.server_name,
            # A Space sets the port in GRADIO_SERVER_PORT, which Gradio only reads without one here
            server_port=None if hosting.on_space() else options.listen_port,
            inbrowser=options.open_browser,
            run_history=options.run_history,
            **launch_kwargs(ctx),
        )
    finally:
        presence.stop()
