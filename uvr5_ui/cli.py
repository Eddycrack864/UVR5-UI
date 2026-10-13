"""Command line options. Flags and defaults are a public contract (scripts and notebooks use them)."""

from argparse import ArgumentParser
from dataclasses import dataclass


@dataclass(frozen=True)
class LaunchOptions:
    share: bool = False
    listen_port: int = 9999
    open_browser: bool = False
    server_name: str | None = None
    run_history: bool = False


def parse_args(argv: list[str] | None = None) -> LaunchOptions:
    parser = ArgumentParser(
        description="Separate audio into multiple stems",
        epilog="Example: python app.py --share --listen-port 8080 --open",
    )
    parser.add_argument("--share", action="store_true",
                        help="Enable sharing of the interface through Gradio's temporary URLs")
    parser.add_argument("--listen-port", type=int, default=9999,
                        help="The listening port that the server will use (default: 9999)")
    parser.add_argument("--open", action="store_true",
                        help="Automatically open the interface in the default web browser")
    parser.add_argument("--server-name", default=None,
                        help='Network interface to bind, e.g. "0.0.0.0" to allow LAN access (default: localhost)')
    parser.add_argument("--run-history", action="store_true",
                        help="Keep a history of the separations in the browser, reachable from the footer")
    args = parser.parse_args(argv)
    return LaunchOptions(share=args.share, listen_port=args.listen_port, open_browser=args.open,
                         server_name=args.server_name, run_history=args.run_history)
