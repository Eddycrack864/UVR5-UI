from tests.conftest import REPO_ROOT


def test_repo_layout():
    assert (REPO_ROOT / "app.py").is_file()
    assert (REPO_ROOT / "assets" / "default_settings.json").is_file()



def test_cli_options():
    from uvr5_ui.cli import parse_args

    default = parse_args([])
    assert (default.share, default.listen_port, default.open_browser, default.run_history) == (False, 9999, False, False)
    options = parse_args(["--share", "--listen-port", "8080", "--open", "--server-name", "0.0.0.0", "--run-history"])
    assert (options.share, options.listen_port, options.open_browser, options.server_name, options.run_history) == (
        True, 8080, True, "0.0.0.0", True)
