import ast

from tools import i18n_scan


def test_every_key_used_in_code_exists_in_en_us():
    assert i18n_scan.main(["--check"]) == 0


def test_extract_keys_finds_i18n_and_marker_calls():
    tree = ast.parse('i18n("A")\nN_("B")\nother("C")\ni18n(variable)\nx = f"{i18n(\'D\')}"\n')
    assert i18n_scan.extract_keys(tree) == {"A", "B", "D"}
